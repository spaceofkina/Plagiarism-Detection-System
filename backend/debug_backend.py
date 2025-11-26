import logging
logging.basicConfig(level=logging.INFO)
print('Testing backend startup...')

try:
    from sentence_transformers import SentenceTransformer
    print('Loading model...')
    model = SentenceTransformer('all-MiniLM-L6-v2')  # Using smaller model for faster loading
    print('Model loaded successfully!')
    
    from main import app
    print('App imported successfully!')
    
    import uvicorn
    print('Starting server on port 8001...')
    uvicorn.run(app, host='0.0.0.0', port=8001, log_level='info')
    
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
    print("\nPress Enter to exit...")
    input()