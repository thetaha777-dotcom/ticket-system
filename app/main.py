from fastapi import FastAPI

app = FastAPI(title="BiletFlow")
@app.get("/")
async def first_api():
        return {'message': 'Hello World!'}

