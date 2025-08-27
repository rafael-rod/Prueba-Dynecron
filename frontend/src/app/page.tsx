import { FileUploader } from './components/FileUploader';

export default function HomePage() {
  return (
    <div className="grid place-items-center py-12">
      <div className="text-center mb-10 max-w-2xl">
        <h1 className="text-3xl md:text-5xl font-bold tracking-tight">
          Chatea con tus Documentos
        </h1>
        <p className="mt-3 text-sm md:text-base text-gray-600 dark:text-gray-300">
          Sube varios archivos y obtén respuestas precisas con citas.
        </p>
      </div>
      <FileUploader />
    </div>
  );
}