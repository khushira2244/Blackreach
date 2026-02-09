Request enters api/main.py.

API layer asks config/settings.py for any needed API keys.

API layer passes the data to core/ to process it.

If needed, Core uses integrations/ to fetch data from another website using HTTPX.

API layer returns the final answer to the u


In Python, these files tell the system: "Treat this folder as a package." Without these files, you wouldn't be able to do things like from core.logic import calculate_total. They allow the different folders to "see" and talk to each other


uvicorn api.main:app --reload 
Part,Meaning,Connection to your Folders
api,The Folder name.,Refers to your api/ directory.
.,Path separator.,Like a slash / in a file path.
main,The File name.,Refers to main.py inside that folder.
:,"The ""Look Inside"" symbol.",Tells Uvicorn to look inside that specific file.
app,The Variable name.,Refers to the line app = FastAPI() in your code.

https://developers.google.com/maps/documentation/routes/compute_route_directions