'use client';

import { useState, useMemo, useEffect } from 'react'; // Importar useMemo y useEffect
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

pdfjs.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.mjs';

interface PdfViewerProps {
  fileHex: string;
  pageNumber?: number;
  textPosition?: {
    start_pos: number;
    end_pos: number;
  };
  onClose: () => void;
}

const hexToArrayBuffer = (hex: string) => {
  const typedArray = new Uint8Array(hex.match(/[\da-f]{2}/gi)!.map(h => parseInt(h, 16)));
  return typedArray.buffer;
};

export function PdfViewer({ fileHex, pageNumber, textPosition, onClose }: PdfViewerProps) {
  const [numPages, setNumPages] = useState<number | null>(null);
  const [currentPage, setCurrentPage] = useState<number>(1);

  // *** CORRECCIÓN 1: Memoizar el objeto 'file' para evitar re-renders innecesarios ***
  const fileData = useMemo(() => ({
    data: hexToArrayBuffer(fileHex),
  }), [fileHex]);

  // Efecto para hacer scroll a la página correcta cuando se proporciona pageNumber
  useEffect(() => {
    if (pageNumber && numPages) {
      // Esperar un poco para que las páginas se rendericen
      setTimeout(() => {
        const pageElement = document.querySelector(`[data-page-number="${pageNumber}"]`);
        if (pageElement) {
          pageElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
          // Actualizar el contador inmediatamente
          setCurrentPage(pageNumber);
          
          // También actualizar después del scroll para asegurar sincronización
          setTimeout(() => {
            setCurrentPage(pageNumber);
          }, 1000);
        }
      }, 500);
    }
  }, [pageNumber, numPages]);

  // Efecto para sincronizar el contador cuando cambia pageNumber
  useEffect(() => {
    if (pageNumber) {
      setCurrentPage(pageNumber);
    }
  }, [pageNumber]);

  // Función para detectar la página actual durante el scroll
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const container = e.currentTarget;
    
    // Obtener todos los elementos de página
    const pageElements = container.querySelectorAll('[data-page-number]');
    if (pageElements.length === 0) return;
    
    // Encontrar qué página está más visible en el viewport
    let mostVisiblePage = 1;
    let maxVisibility = 0;
    
    pageElements.forEach((pageElement) => {
      const rect = pageElement.getBoundingClientRect();
      const containerRect = container.getBoundingClientRect();
      
      // Calcular cuánto de la página está visible
      const visibleHeight = Math.min(rect.bottom, containerRect.bottom) - Math.max(rect.top, containerRect.top);
      const visibility = Math.max(0, visibleHeight / rect.height);
      
      if (visibility > maxVisibility) {
        maxVisibility = visibility;
        mostVisiblePage = parseInt(pageElement.getAttribute('data-page-number') || '1');
      }
    });
    
    // Solo actualizar si hay un cambio significativo y la página es válida
    if (mostVisiblePage !== currentPage && mostVisiblePage >= 1 && mostVisiblePage <= (numPages || 1) && maxVisibility > 0.3) {
      setCurrentPage(mostVisiblePage);
    }
  };

  function onDocumentLoadSuccess({ numPages }: { numPages: number }): void {
    setNumPages(numPages);
  }

  // Función para resaltar texto en el PDF
  const highlightText = (pageElement: HTMLElement) => {
    if (!textPosition) return;
    
    // Buscar elementos de texto en la página
    const textElements = pageElement.querySelectorAll('.react-pdf__Page__textContent');
    
    textElements.forEach((textElement) => {
      const textContent = textElement.textContent || '';
      
      // Si el texto es muy corto, saltarlo
      if (textContent.length < 10) return;
      
      // Crear un resaltado visual en todo el elemento de texto
      // Esto es más confiable que intentar encontrar texto específico
      (textElement as HTMLElement).style.backgroundColor = 'rgba(255, 255, 0, 0.3)';
      (textElement as HTMLElement).style.padding = '2px';
      (textElement as HTMLElement).style.borderRadius = '3px';
      (textElement as HTMLElement).style.border = '2px solid yellow';
    });
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-lg shadow-2xl w-full h-full max-w-6xl max-h-[90vh] flex flex-col">
        <div className="p-4 border-b border-gray-700 flex justify-between items-center">
          <div className="flex items-center space-x-4">
            <h2 className="text-xl font-bold">Visor de PDF</h2>
            {numPages && (
              <span className="text-sm text-gray-300 bg-gray-700 px-3 py-1 rounded-full">
                Página {currentPage} de {numPages}
              </span>
            )}
          </div>
          <button onClick={onClose} className="text-2xl font-bold text-white hover:text-gray-300">&times;</button>
        </div>
        <div className="flex-grow overflow-y-auto p-4" onScroll={handleScroll}>
          <div className="flex justify-center">
            <Document file={fileData} onLoadSuccess={onDocumentLoadSuccess}>
              {Array.from(new Array(numPages), (el, index) => (
                <Page 
                  key={`page_${index + 1}`} 
                  pageNumber={index + 1} 
                  renderTextLayer={true}
                  width={Math.min(800, window.innerWidth - 100)}
                  onRenderSuccess={() => {
                    // Resaltar texto si estamos en la página correcta y tenemos posición
                    if (pageNumber && (index + 1) === pageNumber && textPosition) {
                      setTimeout(() => {
                        const pageElement = document.querySelector(`[data-page-number="${index + 1}"]`);
                        if (pageElement) {
                          highlightText(pageElement as HTMLElement);
                        }
                      }, 200);
                    }
                  }}
                />
              ))}
            </Document>
          </div>
        </div>
      </div>
    </div>
  );
}