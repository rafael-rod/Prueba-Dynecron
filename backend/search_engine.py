from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from typing import Dict, Any, List
from models import DocumentFragment
from config import TOP_K_RESULTS, SIMILARITY_THRESHOLD

def build_index(db: Dict[str, Any]):
    """Build TF-IDF index for documents"""
    all_chunks = [chunk['text'] for doc in db['documents'] for chunk in doc['chunks']]
    if not all_chunks:
        db['word_vectorizer'] = None
        db['char_vectorizer'] = None
        db['word_index'] = None
        db['char_index'] = None
        return

    # Lista simple de stopwords en español (compacta para no añadir dependencias)
    spanish_stopwords = {
        'de','la','que','el','en','y','a','los','del','se','las','por','un','para','con','no','una','su','al','lo','como','más','pero','sus','le','ya','o','este','sí','porque','esta','entre','cuando','muy','sin','sobre','también','me','hasta','hay','donde','quien','desde','todo','nos','durante','todos','uno','les','ni','contra','otros','ese','eso','ante','ellos','e','esto','mí','antes','algunos','qué','unos','yo','otro','otras','otra','él','tanto','esa','estos','mucho','quienes','nada','muchos','cual','poco','ella','estar','estas','algunas','algo','nosotros','mi','mis','tú','te','ti','tu','tus','ellas','nosotras','vosotros','vosotras','os','mío','mía','míos','mías','tuyo','tuya','tuyos','tuyas','suyo','suya','suyos','suyas','nuestro','nuestra','nuestros','nuestras','vuestro','vuestra','vuestros','vuestras','esos','esas','estoy','estás','está','estamos','estáis','están','esté','estés','estemos','estéis','estén','estaré','estarás','estará','estaremos','estaréis','estarán','estaba','estabas','estábamos','estabais','estaban','estuve','estuviste','estuvo','estuvimos','estuvisteis','estuvieron','estuviera','estuvieras','estuviéramos','estuvierais','estuvieran','estuviese','estuvieses','estuviésemos','estuvieseis','estuviesen','estando','estado','estada','estados','estadas','estad','he','has','ha','hemos','habéis','han','haya','hayas','hayamos','hayáis','hayan','habré','habrás','habrá','habremos','habréis','habrán','había','habías','habíamos','habíais','habían','hube','hubiste','hubo','hubimos','hubisteis','hubieron','hubiera','hubieras','hubiéramos','hubierais','hubieran','hubiese','hubieses','hubiésemos','hubieseis','hubiesen','habiendo','habido','habida','habidos','habidas','soy','eres','es','somos','sois','son','sea','seas','seamos','seáis','sean','seré','serás','será','seremos','seréis','serán','era','eras','éramos','erais','eran','fui','fuiste','fue','fuimos','fuisteis','fueron','fuera','fueras','fuéramos','fuerais','fueran','fuese','fueses','fuésemos','fueseis','fuesen','siendo','sido','tengo','tienes','tiene','tenemos','tenéis','tienen','tenga','tengas','tengamos','tengáis','tengan','tendré','tendrás','tendrá','tendremos','tendréis','tendrán','tenía','tenías','teníamos','teníais','tenían','tuve','tuviste','tuvo','tuvimos','tuvisteis','tuvieron','tuviera','tuvieras','tuviéramos','tuvierais','tuvieran','tuviese','tuvieses','tuviésemos','tuvieseis','tuviesen','teniendo','tenido','tenida','tenidos','tenidas'
    }
    combined_stopwords = list(spanish_stopwords.union(ENGLISH_STOP_WORDS))

    # Vectorizador de palabras con lematización simple por acentos y n-gramas 1-2
    word_vectorizer = TfidfVectorizer(
        stop_words=combined_stopwords,
        ngram_range=(1, 2),
        strip_accents='unicode',
        lowercase=True
    )
    word_index = word_vectorizer.fit_transform(all_chunks)

    # Vectorizador de caracteres para captar variaciones morfológicas y errores (char_wb)
    char_vectorizer = TfidfVectorizer(
        analyzer='char_wb',
        ngram_range=(3, 5),
        strip_accents='unicode',
        lowercase=True
    )
    char_index = char_vectorizer.fit_transform(all_chunks)

    db['word_vectorizer'] = word_vectorizer
    db['char_vectorizer'] = char_vectorizer
    db['word_index'] = word_index
    db['char_index'] = char_index
    print("Índice TF-IDF (palabras+caracteres) construido exitosamente.")

def search_query(q: str, db: Dict[str, Any]) -> List[DocumentFragment]:
    """Search for relevant document fragments"""
    if not db or db.get('word_vectorizer') is None or db.get('char_vectorizer') is None:
        return []
    
    try:
        # Consulta en ambos espacios (palabras y caracteres)
        word_q = db['word_vectorizer'].transform([q])
        char_q = db['char_vectorizer'].transform([q])

        word_sim = cosine_similarity(word_q, db['word_index']).flatten()
        char_sim = cosine_similarity(char_q, db['char_index']).flatten()

        # Combinar con un promedio ponderado (más peso a palabras)
        similarities = 0.7 * word_sim + 0.3 * char_sim
        
        # Verificar si hay alguna similitud significativa
        max_similarity = np.max(similarities)
        if max_similarity < SIMILARITY_THRESHOLD:
            return []
        
        top_indices = similarities.argsort()[-TOP_K_RESULTS:][::-1]
        results = []
        all_chunks = [chunk for doc in db['documents'] for chunk in doc['chunks']]
        
        for i in top_indices:
            if similarities[i] > SIMILARITY_THRESHOLD:
                chunk = all_chunks[i]
                results.append(
                    DocumentFragment(
                        text=chunk['text'],
                        document_name=chunk['document_name'],
                        score=round(float(similarities[i]), 4),
                        page_number=chunk.get('page_number'),
                        text_position={
                            'start_pos': chunk.get('start_pos'),
                            'end_pos': chunk.get('end_pos')
                        }
                    )
                )
        return results
    except Exception as e:
        print(f"Error durante la búsqueda: {e}")
        return []
