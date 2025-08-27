'use client';

import { useRouter } from 'next/navigation';
import { useCallback, useState } from 'react';
import { useDropzone, FileRejection } from 'react-dropzone';

export function FileUploader() {
  const [files, setFiles] = useState<File[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const onDrop = useCallback((acceptedFiles: File[], fileRejections: FileRejection[]) => {
    setError(null);
    if (fileRejections.length > 0) {
      setError('Algunos archivos fueron rechazados. Solo se aceptan .txt y .pdf.');
    }
    setFiles(prev => [...prev, ...acceptedFiles].slice(0, 10)); // Limita a 10 archivos
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/plain': ['.txt'],
      'application/pdf': ['.pdf'],
    },
    maxFiles: 10,
  });

  const handleUpload = async () => {
    if (files.length < 3) {
      setError('Por favor, sube entre 3 y 10 archivos.');
      return;
    }
    setIsLoading(true);
    setError(null);

    const formData = new FormData();
    files.forEach(file => formData.append('files', file));

    try {
      const response = await fetch('http://127.0.0.1:8000/ingest', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Error al procesar los archivos.');
      }

      const result = await response.json();
      const sessionId = result.session_id;

      // Obtener el número de chats existentes para generar título secuencial
      const chatsResponse = await fetch('http://127.0.0.1:8000/chats');
      const existingChats = await chatsResponse.json();
      const chatNumber = existingChats.length + 1;
      const dynamicTitle = `Chat ${chatNumber}`;

      // Crear chat en backend
      const createChatRes = await fetch('http://127.0.0.1:8000/chats', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: dynamicTitle, session_id: sessionId })
      });
      if (!createChatRes.ok) {
        const errData = await createChatRes.json();
        throw new Error(errData.detail || 'No se pudo crear el chat.');
      }

      // Guardar nombres de archivo en localStorage solo para UI del popup
      const fileNames = files.map(f => f.name);
      localStorage.setItem('indexedFiles', JSON.stringify(fileNames));

      router.push('/chat');
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Error desconocido';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const removeFile = (fileName: string) => {
    setFiles(files.filter(file => file.name !== fileName));
  };

  return (
    <div className="w-full max-w-2xl mx-auto card p-6 md:p-8">
      <h2 className="text-xl md:text-2xl font-semibold text-center mb-3">Sube tus archivos</h2>
      <p className="text-center text-gray-600 dark:text-gray-300 mb-6">Entre 3 y 10 archivos (.txt o .pdf).</p>
      
      <div
        {...getRootProps()}
        className={`border border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors bg-[--color-card]
          ${isDragActive ? 'border-[--color-primary]' : 'border-[--color-border] hover:border-[--color-primary]'}`}
      >
        <input {...getInputProps()} />
        {isDragActive ? (
          <p className="text-sm">Suelta los archivos aquí…</p>
        ) : (
          <p className="text-sm">Arrastra y suelta los archivos aquí, o haz clic para seleccionarlos.</p>
        )}
      </div>

      {files.length > 0 && (
        <div className="mt-8">
          <h3 className="text-sm font-semibold">Archivos seleccionados ({files.length}/10):</h3>
          <ul className="mt-4 space-y-2">
            {files.map(file => (
              <li key={file.name} className="flex justify-between items-center bg-[--color-muted] border border-[--color-border] p-3 rounded-md">
                <span className="truncate text-sm">{file.name}</span>
                <button
                  onClick={() => removeFile(file.name)}
                  className="text-red-500 hover:text-red-400 font-bold ml-4"
                >
                  &times;
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
      
      {error && <p className="mt-4 text-center text-red-500">{error}</p>}

      <div className="mt-8 text-center">
        <button
          onClick={handleUpload}
          disabled={isLoading || files.length < 3 || files.length > 10}
          className="btn btn-primary w-full md:w-auto disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Procesando...' : 'Indexar y Chatear'}
        </button>
      </div>
    </div>
  );
}