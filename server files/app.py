from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/")
def index():
    return jsonify({"message": "Hello from EC2!"})

# If your script is a function you want to call:
@app.route("/run", methods=["POST"])
def run_script():
    # your script logic here
    data = {"result": "script ran successfully"}
    return jsonify(data)

if __name__ == "__main__":
    app.run()
