import React, { useCallback, useRef, useState } from 'react';

// The upstream Strudel control stores selected files in IndexedDB and labels
// them "user". Strudel Voice sends them to its local backend so speech can be
// transcribed, sliced, and registered in the voice/mix banks.
export default function ImportSoundsButton({ onComplete }) {
  const fileUploadRef = useRef(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState('');
  const onChange = useCallback(async () => {
    const files = Array.from(fileUploadRef.current?.files || []);
    if (!files.length) return;
    setIsUploading(true);
    setError('');
    try {
      if (typeof window.strudelVoiceImportAudioPack !== 'function') {
        throw new Error('Strudel Voice is still loading. Refresh the page and try again.');
      }
      await window.strudelVoiceImportAudioPack(files);
      onComplete?.();
    } catch (importError) {
      setError(importError instanceof Error ? importError.message : String(importError));
    } finally {
      setIsUploading(false);
      // Let the user import the same folder again after delete-all.
      if (fileUploadRef.current) fileUploadRef.current.value = '';
    }
  }, [onComplete]);

  return (
    <div>
      <label
        style={{ alignItems: 'center', borderColor: 'red', border: 1 }}
        className="flex bg-background  p-4  w-fit rounded-xl hover:opacity-50 whitespace-nowrap cursor-pointer"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={1.5}
          stroke="currentColor"
          className="size-6 mr-2"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M7.5 7.5h-.75A2.25 2.25 0 0 0 4.5 9.75v7.5a2.25 2.25 0 0 0 2.25 2.25h7.5a2.25 2.25 0 0 0 2.25-2.25v-7.5a2.25 2.25 0 0 0-2.25-2.25h-.75m0-3-3-3m0 0-3 3m3-3v11.25m6-2.25h.75a2.25 2.25 0 0 1 2.25 2.25v7.5a2.25 2.25 0 0 1-2.25 2.25h-7.5a2.25 2.25 0 0 1-2.25-2.25v-.75"
          />
        </svg>

        <input
          disabled={isUploading}
          ref={fileUploadRef}
          id="audio_file"
          style={{ display: 'none' }}
          type="file"
          directory=""
          webkitdirectory=""
          multiple
          accept="audio/*, .wav, .mp3, .m4a, .flac, .aac, .ogg, .opus, .webm"
          onChange={onChange}
        />
        {isUploading ? 'analysing voice audio...' : 'import and analyse audio folder'}
      </label>
      <p className="text-xs mt-2 max-w-xl">
        Audio is transcribed and sliced into the <b>voice</b> and <b>mix</b> tabs; it is not added to <b>user</b>.
      </p>
      {error && <p className="text-xs mt-2 text-red-500">{error}</p>}
    </div>
  );
}
