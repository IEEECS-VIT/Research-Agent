import os
import sys
import chromadb
from chromadb.config import Settings

def main():
    # Path to Chroma DB (matching CHROMA_DATA_DIR in chroma_store.py)
    USER_HOME = os.path.expanduser("~")
    db_path = os.path.join(USER_HOME, ".local_chroma_data_v12")
    
    print(f"Connecting to ChromaDB at: {db_path}...")
    
    if not os.path.exists(db_path):
        print(f"Error: Chroma database directory does not exist at {db_path}.")
        return

    try:
        client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(anonymized_telemetry=False)
        )
        
        collections = client.list_collections()
        print(f"Available collections: {[c.name for c in collections]}")
        
        if not collections:
            print("No collections found in ChromaDB.")
            return
            
        collection_name = "research_papers_v12"
        print(f"\nFetching data from collection: '{collection_name}'...")
        collection = client.get_collection(name=collection_name)
        
        data = collection.get()
        ids = data.get("ids", [])
        metadatas = data.get("metadatas", [])
        documents = data.get("documents", [])
        
        total_records = len(ids)
        print(f"Total documents/chunks stored: {total_records}")
        
        if total_records == 0:
            print("No records found in this collection.")
            return
            
        # Group by file name
        files = {}
        for idx in range(total_records):
            meta = metadatas[idx]
            filename = meta.get("filename", "unknown")
            source_type = meta.get("source_type", "unknown")
            version_id = meta.get("version_id", "unknown")
            
            key = (filename, source_type, version_id)
            if key not in files:
                files[key] = []
            files[key].append(idx)
            
        print("\n=== INGESTED DOCUMENTS SUMMARY ===")
        for (filename, source_type, version_id), indices in files.items():
            print(f"- Filename: {filename}")
            print(f"  Source Type: {source_type.upper()}")
            print(f"  Ingestion Version: {version_id}")
            print(f"  Number of Chunks: {len(indices)}")
            print("-" * 40)
            
        # Prompt user for detailed view
        print("\nTo view detailed content, you can print them out. Showing a sample of the first 3 chunks:")
        sample_count = min(3, total_records)
        for idx in range(sample_count):
            print(f"\n[Chunk {idx+1}/{total_records}] ID: {ids[idx]}")
            print(f"Metadata: {metadatas[idx]}")
            print(f"Content Preview:\n{documents[idx][:300]}...")
            print("=" * 60)
            
    except Exception as e:
        print(f"Error querying ChromaDB: {e}")

if __name__ == "__main__":
    main()
