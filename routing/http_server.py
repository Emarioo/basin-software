from http.server import HTTPServer, SimpleHTTPRequestHandler
import os, signal, sys

class NoListingHandler(SimpleHTTPRequestHandler):
    def list_directory(self, path):
        self.send_error(403, "Directory listing is forbidden")
        return None

    def do_GET(self):
        # Only allow access to files under serve/.well-known/
        if self.path.startswith("/.well-known/"):

            return super().do_GET()
        else:
            self.send_error(403, "Forbidden")
    
   # def log_message(self, format, *args):
   #     print(f"[{self.client_address[0]}] requested {self.path}")


os.chdir("serve")  # Change root dir

server = HTTPServer(("0.0.0.0", 80), NoListingHandler)

def handle_sigint(signal_num, frame):
    sys.exit(0)

signal.signal(signal.SIGINT, handle_sigint)

print("Serving on port 80")
server.serve_forever()