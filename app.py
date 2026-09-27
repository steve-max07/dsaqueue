import subprocess
import os
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS

app = Flask(__name__)
# Enable CORS so your local HTML file can connect to this API without browser blocks
CORS(app)

# 1. RESOLVE ABSOLUTE PATH FOR WINDOWS/LINUX BINARIES
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if os.name == 'nt':
    exe_path = os.path.join(BASE_DIR, "queue_app.exe")
else:
    exe_path = os.path.join(BASE_DIR, "queue_app")

print(f"[SYSTEM] Starting backend connection to C binary: {exe_path}")

# 2. START THE PERSISTENT BACKGROUND C SUBPROCESS PIPELINE
try:
    c_process = subprocess.Popen(
        [exe_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        bufsize=1  # Line buffered for immediate transmission
    )
    print("[SYSTEM] C process launched successfully and listening on stdin.")
except Exception as e:
    print(f"[CRITICAL ERROR] Could not locate or start C application: {e}")
    print("-> Please ensure you compiled queue_app.c into queue_app.exe in the same folder!")

@app.route('/')
def home():
    try:
        with open("index.html", "r") as f:
            return render_template_string(f.read())
    except FileNotFoundError:
        return "index.html file not found in this folder.", 404


# 3. ROUTE: REGISTER A PATIENT (ENQUEUE)
@app.route('/api/register', methods=['POST'])
def register():
    # Strip incoming values and replace inner spaces to prevent C scanf fragmentation
    name = request.form.get('name', '').strip().replace(" ", "_")
    age = request.form.get('age', '0').strip()
    ailment = request.form.get('ailment', '').strip().replace(" ", "_")

    print(f"\n[API POST] /api/register -> Name: {name}, Age: {age}, Ailment: {ailment}")

    try:
        # Write arguments as a space-separated row to match C's scanf loop format
        c_process.stdin.write(f"1 {name} {age} {ailment}\n")
        c_process.stdin.flush()
    except Exception as e:
        print(f"[ERROR] Failed writing registration command to C: {e}")
        return jsonify({"error": "C pipeline connection dead"}), 500

    try:
        response = c_process.stdout.readline().strip()
        print(f"[C RESPONSE] {response}")
        
        if response == "ERROR_FULL" or not response:
            return jsonify({"error": "Hospital is at max capacity"}), 500
        
        # Split "SUCCESS_REG <id>" to extract the assigned numeric token
        parts = response.split()
        if len(parts) >= 2:
            token_id = int(parts[1])
            return jsonify({"status": "success", "id": token_id})
        else:
            return jsonify({"error": "Malformed register output from C"}), 500
    except Exception as e:
        print(f"[ERROR] Parsing response failed: {e}")
        return jsonify({"error": "Data parsing failure"}), 500


# 4. ROUTE: CALL NEXT PATIENT (DEQUEUE)
@app.route('/api/dequeue', methods=['POST'])
def dequeue():
    print("\n[API POST] /api/dequeue -> Doctor requested next patient.")
    
    try:
        c_process.stdin.write("2\n")
        c_process.stdin.flush()
    except Exception as e:
        print(f"[ERROR] Failed writing dequeue command to C: {e}")
        return jsonify({"status": "empty", "error": "C pipeline connection dead"}), 500

    try:
        response = c_process.stdout.readline().strip()
        print(f"[C RESPONSE] {response}")
        
        if response == "EMPTY" or not response or "LIST_COUNT" in response:
            return jsonify({"status": "empty"})
        
        # BULLETPROOF PARSING: Split using the pipe character (|)
        item_parts = response.split("|")
        
        if len(item_parts) < 4:
            return jsonify({"status": "empty", "error": "Malformed row structure"})
            
        # Extract ID safely by grabbing only the numeric portion after text prefixes
        raw_id = item_parts[0].split()[-1]
        p_id = int(raw_id)
        
        name = item_parts[1]
        age = int(item_parts[2])
        ailment = item_parts[3]
        
        return jsonify({
            "status": "called",
            "id": p_id,
            "name": name.replace("_", " "),
            "age": age,
            "ailment": ailment.replace("_", " ")
        })
    except Exception as e:
        print(f"[ERROR] Dequeue data extraction failed: {e}")
        return jsonify({"status": "empty", "error": "Parser failed"}), 500


# 5. ROUTE: REFRESH ACTIVE MONITOR DATA (GET LIST)
@app.route('/api/list', methods=['GET'])
def get_list():
    try:
        c_process.stdin.write("3\n")
        c_process.stdin.flush()
        
        count_response = c_process.stdout.readline().strip()
        if not count_response or "LIST_COUNT" not in count_response:
            return jsonify([])
            
        parts = count_response.split()
        count = int(parts[1])
        patients = []
        
        # Loop through and unpack each patient line printed by C
        for _ in range(count):
            item_line = c_process.stdout.readline().strip()
            
            # Skip any misaligned lines that lack structural pipe marks
            if "|" not in item_line:
                continue
                
            item_parts = item_line.split("|")
            if len(item_parts) < 4:
                continue
                
            # Extract ID safely by isolating the number from text prefixes
            raw_id = item_parts[0].split()[-1]
            p_id = int(raw_id)
            
            p_name = item_parts[1]
            p_age = int(item_parts[2])
            p_ailment = item_parts[3]
            
            patients.append({
                "id": p_id,
                "name": p_name.replace("_", " "),
                "age": p_age,
                "ailment": p_ailment.replace("_", " ")
            })
        return jsonify(patients)
    except Exception as e:
        print(f"[DEBUG MONITOR ERROR] Safe caught desync: {e}")
        return jsonify([])


# 6. SYSTEM LIFECYCLE MANAGEMENT CLEANUP HOOK
if __name__ == '__main__':
    try:
       port = int(os.environ.get("PORT", 10000))
       app.run(host='0.0.0.0', port=port)
    finally:
        print("\n[SYSTEM] Shutting down. Terminating background C process...")
        try:
            c_process.stdin.write("4\n")
            c_process.stdin.flush()
            c_process.terminate()
        except:
            pass
