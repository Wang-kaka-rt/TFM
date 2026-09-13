import React, { useCallback, useRef, useState } from 'react';

const SUPPORTED_AUDIO = /\.(wav|mp3|m4a|flac|aac|ogg|opus|webm)$/i;

// The upstream Strudel control stores selected files in IndexedDB and labels
// them "user". Strudel Voice sends them to its local backend so speech can be
// transcribed, sliced, and registered in the voice/mix banks.
export default function ImportSoundsButton({ onComplete }) {
  const fileUploadRef = useRef(null);
  const [isUploading, setIsUploading] = useState(false);
  const [importMode, setImportMode] = useState('');
  const [error, setError] = useState('');
  const onChange = useCallback(async () => {
    const selectedFiles = Array.from(fileUploadRef.current?.files || []);
    if (!selectedFiles.length) return;
    // A Strudel Voice result folder contains a manifest plus hundreds or
    // thousands of generated clips. Restore it rather than re-uploading every
    // clip for a second transcription pass.
    const generatedManifest = selectedFiles.find((file) => file.name.toLowerCase() === 'samples.json');
    const isGeneratedBank = Boolean(generatedManifest);
    const generatedBankName = String(generatedManifest?.webkitRelativePath || '')
      .split('/')
      .filter(Boolean)[0] || '';
    // Folder pickers can include .DS_Store, README files and thumbnails. Send
    // only formats the backend can decode, protecting the selected voice bank.
    const files = selectedFiles.filter((file) => SUPPORTED_AUDIO.test(file.name));
    if (!isGeneratedBank && !files.length) {
      setError('No supported audio files were found in the selected folder.');
      if (fileUploadRef.current) fileUploadRef.current.value = '';
      return;
    }
    setIsUploading(true);
    setImportMode(isGeneratedBank ? 'restore' : 'analyse');
    setError(isGeneratedBank || files.length === selectedFiles.length ? '' : `Ignored ${selectedFiles.length - files.length} non-audio file(s).`);
    try {
      if (isGeneratedBank) {
        if (typeof window.strudelVoiceRestoreGeneratedBank !== 'function') {
          throw new Error('Strudel Voice is still loading. Refresh the page and try again.');
        }
        await window.strudelVoiceRestoreGeneratedBank(generatedBankName);
      } else if (typeof window.strudelVoiceImportAudioPack !== 'function') {
        throw new Error('Strudel Voice is still loading. Refresh the page and try again.');
      } else {
        await window.strudelVoiceImportAudioPack(files);
      }
      onComplete?.();
    } catch (importError) {
      setError(importError instanceof Error ? importError.message : String(importError));
    } finally {
      setIsUploading(false);
      setImportMode('');
      // Let the user import the same folder again after delete-all.
      if (fileUploadRef.current) fileUploadRef.current.value = '';
    }
  }, [onComplete]);

  return (
    <div>
      <label
        style={{
          alignItems: 'center',
          opacity: isUploading ? 0.7 : 1,
          cursor: isUploading ? 'wait' : 'pointer',
        }}
        className="flex bg-background p-4 w-fit rounded-xl hover:opacity-50 whitespace-nowrap cursor-pointer"
      >
        {isUploading ? (
          <span
            aria-label="Analysing audio"
            role="status"
            className="animate-spin"
            style={{
              width: 20,
              height: 20,
              marginRight: 10,
              border: '3px solid currentColor',
              borderRightColor: 'transparent',
              borderRadius: '50%',
            }}
          />
        ) : (
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
        )}

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
        {isUploading
          ? importMode === 'restore'
            ? 'restoring generated samples...'
            : 'analysing audio — please wait...'
          : 'import and analyse audio folder'}
      </label>
      {isUploading && (
        <p className="text-xs mt-2 max-w-xl" aria-live="polite">
          {importMode === 'restore'
            ? 'Restoring the generated samples directly into voice and mix. Do not refresh the page yet.'
            : 'Processing is running on the local server. Do not refresh the page or import another folder until it finishes.'}
        </p>
      )}
      <p className="text-xs mt-2 max-w-xl">
        Raw audio is transcribed and sliced into <b>voice</b> and <b>mix</b>. A folder containing <code>samples.json</code> restores its generated samples directly.
      </p>
      {error && <p className="text-xs mt-2 text-red-500">{error}</p>}
    </div>
  );
}
