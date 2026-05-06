import { code2hash, errorLogger, evalScope, hash2code, logger } from '@strudel/core';
import { settingPatterns, settingsMap } from '../settings.mjs';
import { setVersionDefaults } from '@strudel/webaudio';
import { getMetadata } from '../metadata_parser';
import { isTauri } from '../tauri.mjs';
import './Repl.css';
import { createClient } from '@supabase/supabase-js';
import { writeText } from '@tauri-apps/plugin-clipboard-manager';
import { $featuredPatterns /* , loadDBPatterns */ } from '@src/user_pattern_utils.mjs';
import {
  registerSamplesFromDB,
  uploadSampleRecordsToDB,
  userSamplesDBConfig,
} from '@src/repl/idbutils.mjs';

// Create a single supabase client for interacting with your database
export const supabase = createClient(
  'https://pidxdsxphlhzjnzmifth.supabase.co',
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBpZHhkc3hwaGxoempuem1pZnRoIiwicm9sZSI6ImFub24iLCJpYXQiOjE2NTYyMzA1NTYsImV4cCI6MTk3MTgwNjU1Nn0.bqlw7802fsWRnqU5BLYtmXk_k-D1VFmbkHMywWc15NM',
);

let dbLoaded;
/* if (typeof window !== 'undefined') {
  dbLoaded = loadDBPatterns();
} */

export async function initCode() {
  // load code from url hash (either short hash from database or decode long hash)
  try {
    const initialUrl = window.location.href;
    const hash = initialUrl.split('?')[1]?.split('#')?.[0]?.split('&')[0];
    const codeParam = window.location.href.split('#')[1] || '';
    if (codeParam) {
      // looking like https://strudel.cc/#ImMzIGUzIg%3D%3D (hash length depends on code length)
      return hash2code(codeParam);
    } else if (hash) {
      // looking like https://strudel.cc/?J01s5i1J0200 (fixed hash length)
      return supabase
        .from('code_v1')
        .select('code')
        .eq('hash', hash)
        .then(({ data, error }) => {
          if (error) {
            console.warn('failed to load hash', error);
          }
          if (data.length) {
            //console.log('load hash from database', hash);
            return data[0].code;
          }
        });
    }
  } catch (err) {
    console.warn('failed to decode', err);
  }
}

function getUrlParamsSafe() {
  try {
    const url = new URL(window.location.href);
    return url.searchParams;
  } catch {
    return new URLSearchParams();
  }
}

export function initializeStrudelVoiceGlobalsFromUrl() {
  const params = getUrlParamsSafe();
  const sessionId = (params.get('svSession') || '').trim();
  if (!sessionId) {
    return false;
  }
  const baseUrl = (params.get('svBase') || window.location.origin).trim().replace(/\/+$/, '');
  let currentSessionId = sessionId;
  const moduleCache = new Map();
  const SESSION_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/;

  const resolveSessionIdCandidate = (requestedSessionId) => {
    if (requestedSessionId == null) {
      return '';
    }
    if (typeof requestedSessionId === 'string') {
      return requestedSessionId;
    }
    if (typeof requestedSessionId === 'object') {
      const candidate =
        requestedSessionId.sessionId ??
        requestedSessionId.session_id ??
        requestedSessionId.value ??
        requestedSessionId.detail?.sessionId ??
        requestedSessionId.detail?.session_id ??
        '';
      return typeof candidate === 'string' ? candidate : '';
    }
    return String(requestedSessionId);
  };

  const normalizeSessionId = (requestedSessionId) => {
    let value = resolveSessionIdCandidate(requestedSessionId).trim();
    if (!value || value === '[object Object]') {
      value = String(currentSessionId ?? '').trim();
    }
    if (!value) {
      throw new Error('Strudel-Voice session id is empty.');
    }
    if (!SESSION_ID_PATTERN.test(value)) {
      throw new Error('Strudel-Voice session id is invalid. Use letters, numbers, "_" or "-".');
    }
    return value;
  };

  const request = async (path, requestedSessionId) => {
    const response = await fetch(`${baseUrl}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: requestedSessionId }),
    });
    if (!response.ok) {
      const detail = await response.text();
      throw new Error(`Strudel-Voice API error ${response.status}: ${detail}`);
    }
    return response.json();
  };

  const loadModule = async (requestedSessionId) => {
    if (moduleCache.has(requestedSessionId)) {
      return moduleCache.get(requestedSessionId);
    }
    const moduleUrl = `${baseUrl}/strudel/${encodeURIComponent(requestedSessionId)}?t=${Date.now()}`;
    try {
      const mod = await import(moduleUrl);
      moduleCache.set(requestedSessionId, mod);
      return mod;
    } catch {
      return null;
    }
  };

  const getSamples = async (requestedSessionId) => {
    const mod = await loadModule(requestedSessionId);
    return mod?.strudelVoiceSamples ?? { words: [], phrases: [], sentences: [], letters: [] };
  };

  const normalizeSoundName = (value, fallback) => {
    const label = String(value || fallback || 'voice')
      .trim()
      .replace(/[\\/]/g, ' ')
      .replace(/\s+/g, '_')
      .replace(/[^\p{L}\p{N}_#.-]+/gu, '')
      .replace(/^_+|_+$/g, '');
    return label || fallback || 'voice';
  };

  const importSamples = async (requestedSessionId = currentSessionId, mode = 'sentences') => {
    const sid = normalizeSessionId(requestedSessionId);
    currentSessionId = sid;
    const selectedMode = String(mode || 'sentences');
    const response = await fetch(`${baseUrl}/samples/${encodeURIComponent(sid)}/manifest?t=${Date.now()}`);
    if (!response.ok) {
      const detail = await response.text();
      throw new Error(`Strudel-Voice samples manifest error ${response.status}: ${detail}`);
    }
    const manifest = await response.json();
    const samples = Array.isArray(manifest?.[selectedMode]) ? manifest[selectedMode] : [];
    if (!samples.length) {
      throw new Error(`No "${selectedMode}" samples found for session "${sid}". Stop recording first.`);
    }

    const records = await Promise.all(
      samples.map(async (sample, index) => {
        const sampleUrl = sample.url || `${baseUrl}/samples/${encodeURIComponent(sid)}/${sample.path}`;
        const audioResponse = await fetch(sampleUrl);
        if (!audioResponse.ok) {
          throw new Error(`Failed to fetch sample ${sampleUrl}: ${audioResponse.status}`);
        }
        const blob = await audioResponse.blob();
        const fileName = String(sample.path || sampleUrl).split('/').pop() || `sample_${index + 1}.wav`;
        const soundName = normalizeSoundName(sample.text || sample.name, `${selectedMode}_${index + 1}`);
        return {
          id: `${sid}/${selectedMode}/${soundName}/${fileName}`,
          title: fileName,
          blob,
        };
      }),
    );

    await uploadSampleRecordsToDB(userSamplesDBConfig, records);
    await new Promise((resolve) => {
      registerSamplesFromDB(userSamplesDBConfig, () => {
        settingsMap.setKey('soundsFilter', 'user');
        resolve();
      });
    });
    logger(`Imported ${records.length} Strudel Voice ${selectedMode} samples into user sounds`, 'success');
    return { sessionId: sid, mode: selectedMode, count: records.length };
  };

  const start = async (requestedSessionId = currentSessionId) => {
    const sid = normalizeSessionId(requestedSessionId);
    currentSessionId = sid;
    return request('/start', sid);
  };

  const reload = async (requestedSessionId = currentSessionId) => {
    const sid = normalizeSessionId(requestedSessionId);
    currentSessionId = sid;
    const result = await request('/reload', sid);
    moduleCache.delete(sid);
    globalThis.strudelVoiceSamples = await getSamples(sid);
    return result;
  };

  const stop = async (requestedSessionId = currentSessionId) => {
    const sid = normalizeSessionId(requestedSessionId);
    currentSessionId = sid;
    return request('/stop', sid);
  };

  globalThis.start = start;
  globalThis.reload = reload;
  globalThis.stop = stop;
  globalThis.strudelVoiceStart = start;
  globalThis.strudelVoiceReload = reload;
  globalThis.strudelVoiceStop = stop;
  globalThis.strudelVoiceImportSamples = importSamples;
  getSamples(currentSessionId)
    .then((samples) => {
      globalThis.strudelVoiceSamples = samples;
    })
    .catch(() => {
      globalThis.strudelVoiceSamples = { words: [], phrases: [], sentences: [], letters: [] };
    });

  return true;
}

export function buildStrudelVoiceBootstrapFromUrl() {
  const params = getUrlParamsSafe();
  const sessionId = (params.get('svSession') || '').trim();
  if (!sessionId) {
    return '';
  }
  return `/* Strudel-Voice controls are preloaded.
Use:
await start('demo')
await reload()
await stop()
*/`;
}

export const parseJSON = (json) => {
  json = json != null && json.length ? json : '{}';
  try {
    return JSON.parse(json);
  } catch {
    return '{}';
  }
};

export async function getRandomTune() {
  await dbLoaded;
  const featuredTunes = Object.entries($featuredPatterns.get());
  const randomItem = (arr) => arr[Math.floor(Math.random() * arr.length)];
  const [_, data] = randomItem(featuredTunes);
  return data;
}

export function loadModules() {
  let modules = [
    import('@strudel/core'),
    import('@strudel/draw'),
    import('@strudel/edo'),
    import('@strudel/tonal'),
    import('@strudel/mini'),
    import('@strudel/xen'),
    import('@strudel/webaudio'),
    import('@strudel/codemirror'),
    import('@strudel/hydra'),
    import('@strudel/serial'),
    import('@strudel/soundfonts'),
    import('@strudel/csound'),
    import('@strudel/tidal'),
    import('@strudel/gamepad'),
    import('@strudel/motion'),
    import('@strudel/mqtt'),
    import('@strudel/mondo'),
  ];
  if (isTauri()) {
    modules = modules.concat([
      import('@strudel/desktopbridge/loggerbridge.mjs'),
      import('@strudel/desktopbridge/midibridge.mjs'),
      import('@strudel/desktopbridge/oscbridge.mjs'),
    ]);
  } else {
    modules = modules.concat([import('@strudel/midi'), import('@strudel/osc')]);
  }

  return evalScope(settingPatterns, ...modules);
}
// confirm dialog is a promise in webkit and a boolean in other browsers... normalize it to be a promise everywhere
export function confirmDialog(msg) {
  const confirmed = confirm(msg);
  if (confirmed instanceof Promise) {
    return confirmed;
  }
  return new Promise((resolve) => {
    resolve(confirmed);
  });
}
export const SETTING_CHANGE_RELOAD_MSG = 'Changing this setting requires the window to reload itself. OK?';

export function confirmAndReloadPage(onSuccess) {
  confirmDialog(SETTING_CHANGE_RELOAD_MSG).then((r) => {
    if (r == true) {
      try {
        onSuccess();
        return window.location.reload();
      } catch (e) {
        errorLogger(e);
      }
    }
  });
}
//RIP due to SPAM
// let lastShared;
// export async function shareCode(codeToShare) {
//   // const codeToShare = activeCode || code;
//   if (lastShared === codeToShare) {
//     logger(`Link already generated!`, 'error');
//     return;
//   }

//   confirmDialog(
//     'Do you want your pattern to be public? If no, press cancel and you will get just a private link.',
//   ).then(async (isPublic) => {
//     const hash = nanoid(12);
//     const shareUrl = window.location.origin + window.location.pathname + '?' + hash;
//     const { error } = await supabase.from('code_v1').insert([{ code: codeToShare, hash, ['public']: isPublic }]);
//     if (!error) {
//       lastShared = codeToShare;
//       // copy shareUrl to clipboard
//       if (isTauri()) {
//         await writeText(shareUrl);
//       } else {
//         await navigator.clipboard.writeText(shareUrl);
//       }
//       const message = `Link copied to clipboard: ${shareUrl}`;
//       alert(message);
//       // alert(message);
//       logger(message, 'highlight');
//     } else {
//       console.log('error', error);
//       const message = `Error: ${error.message}`;
//       // alert(message);
//       logger(message);
//     }
//   });
// }

export async function shareCode(codeToShare) {
  try {
    const hash = '#' + code2hash(codeToShare);
    const shareUrl = window.location.origin + window.location.pathname + hash;
    if (isTauri()) {
      await writeText(shareUrl);
    } else {
      await navigator.clipboard.writeText(shareUrl);
    }
    const message = `Link copied to clipboard!`;
    alert(message);
    logger(message, 'highlight');
  } catch (e) {
    console.error(e);
  }
}

export const isIframe = () => window.location !== window.parent.location;
function isCrossOriginFrame() {
  try {
    return !window.top.location.hostname;
  } catch (e) {
    return true;
  }
}

export const isUdels = () => {
  if (isCrossOriginFrame()) {
    return false;
  }
  return window.top?.location?.pathname.includes('udels');
};

export function setVersionDefaultsFrom(code) {
  try {
    const metadata = getMetadata(code);
    setVersionDefaults(metadata.version);
  } catch (err) {
    console.error('Error parsing metadata..');
    console.error(err);
  }
}
