from flask import Flask, render_template, request, jsonify
import hashlib
import math

app = Flask(__name__)

class PairHash:
    def __call__(self, p):
        h1 = hash(p[0])
        h2 = hash(p[1])
        return h1 ^ (h2 + 0x9e3779b9 + (h1 << 6) + (h1 >> 2))

class ConsistentHash:
    def __init__(self):
        self.machines = []
        self.machine_ids = set()
        self.data_map = {}
    
    def splitmix64(self, x):
        x += 0x9e3779b97f4a7c15
        x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9
        x = (x ^ (x >> 27)) * 0x94d049bb133111eb
        return x ^ (x >> 31)
    
    def get_hash(self, x):
        h = self.splitmix64(x)
        return h & 0x7FFFFFFF
    
    def get_previous_hash(self, x):
        low = 0
        high = len(self.machines) - 1
        while low <= high:
            mid = (low + high)//2
            mid_hash = self.machines[mid]
            if low == high:
                if self.machines[low] >= x:
                    prev_index = (low - 1 + len(self.machines)) % len(self.machines)
                    return self.machines[prev_index]
                else:
                    return self.machines[low]
            if x > mid_hash:
                low = mid + 1
            elif x < mid_hash:
                high = mid - 1
            else:
                return mid_hash
        return -1
    
    def get_next_hash(self, x):
        if len(self.machines) == 0:
            return -1
            
        low = 0
        high = len(self.machines) - 1
        while low <= high:
            mid = (low + high)//2
            mid_hash = self.machines[mid]
            if low == high:
                if self.machines[low] >= x:
                    return self.machines[low]
                else:
                    next_index = (low + 1) % len(self.machines)
                    return self.machines[next_index]
            if x > mid_hash:
                low = mid + 1
            elif x < mid_hash:
                high = mid - 1
            else:
                return mid_hash
        
        # 如果没有找到合适的，返回第一个机器（环形结构）
        return -1
    
    def add_machine(self, machine_id):
        if machine_id in self.machine_ids:
            return {
                "success": False,
                "message": "Machine already exists",
                "details": {
                    "machine_id": machine_id,
                    "existing_machines": list(self.machine_ids)
                }
            }
        
        hash_val = self.get_hash(machine_id)
        
        # Check for hash collision
        if hash_val in self.machines:
            return {
                "success": False,
                "message": "Hash collision detected",
                "details": {
                    "machine_id": machine_id,
                    "hash_value": hash_val,
                    "existing_hashes": self.machines.copy()
                }
            }
        
        self.machine_ids.add(machine_id)
        data_reassigned_count = 0
        
        if len(self.machine_ids) == 1:
            self.machines.append(hash_val)
            self.data_map[hash_val] = set()
            
            return {
                "success": True,
                "message": "Machine added successfully",
                "details": {
                    "machine_id": machine_id,
                    "machine_hash": hash_val,
                    "machine_count": len(self.machine_ids),
                    "data_reassigned": 0,
                    "is_first_machine": True
                }
            }
        
        next_machine_hash = self.get_next_hash(hash_val)
        previous_machine_hash = self.get_previous_hash(hash_val)
        
        # Initialize data set for new machine
        self.data_map[hash_val] = set()
        
        # Reassign data if needed
        if next_machine_hash == self.machines[0] and previous_machine_hash == self.machines[-1]:
            if hash_val > previous_machine_hash:
                # Reassign data from next machine
                to_move = []
                for item in self.data_map[next_machine_hash]:
                    if item[1] <= hash_val and item[1] > previous_machine_hash:
                        to_move.append(item)
                data_reassigned_count = len(to_move)
                for item in to_move:
                    self.data_map[next_machine_hash].remove(item)
                    self.data_map[hash_val].add(item)
            else:
                to_move = []
                for item in self.data_map[next_machine_hash]:
                    if item[1] <= hash_val or item[1] > previous_machine_hash:
                        to_move.append(item)
                data_reassigned_count = len(to_move)
                for item in to_move:
                    self.data_map[next_machine_hash].remove(item)
                    self.data_map[hash_val].add(item)
        else:
            to_move = []
            for item in self.data_map[next_machine_hash]:
                if item[1] <= hash_val:
                    to_move.append(item)
            data_reassigned_count = len(to_move)
            for item in to_move:
                self.data_map[next_machine_hash].remove(item)
                self.data_map[hash_val].add(item)
        
        # Insert machine into sorted list
        insert_pos = 0
        while insert_pos < len(self.machines) and self.machines[insert_pos] < hash_val:
            insert_pos += 1
        self.machines.insert(insert_pos, hash_val)
        
        return {
            "success": True,
            "message": "Machine added successfully",
            "details": {
                "machine_id": machine_id,
                "machine_hash": hash_val,
                "machine_count": len(self.machine_ids),
                "data_reassigned": data_reassigned_count,
                "previous_machine_hash": previous_machine_hash,
                "next_machine_hash": next_machine_hash
            }
        }
    
    def delete_machine(self, machine_id):
        if machine_id not in self.machine_ids:
            return {"success": False, "message": "Machine not found"}
        
        hash_val = self.get_hash(machine_id)
        
        if len(self.machine_ids) == 1:
            data_count = sum(len(items) for items in self.data_map.values())
            self.machines.clear()
            self.machine_ids.clear()
            self.data_map.clear()
            return {
                "success": True,
                "message": "Last machine deleted",
                "details": {
                    "deleted_machine_id": machine_id,
                    "deleted_machine_hash": hash_val,
                    "data_count": data_count,
                    "action": "All data cleared"
                }
            }
        
        if hash_val not in self.data_map:
            return {"success": False, "message": "Machine hash not found"}
        
        # Get data count before deletion
        data_count = len(self.data_map[hash_val])
        next_hash = self.get_next_hash((hash_val+1)%2147483647)
        
        # Merge data to next machine
        if hash_val in self.data_map:
            self.data_map[next_hash].update(self.data_map[hash_val])
            del self.data_map[hash_val]
        
        self.machine_ids.remove(machine_id)
        self.machines.remove(hash_val)
        
        return {
            "success": True,
            "message": "Machine deleted successfully",
            "details": {
                "deleted_machine_id": machine_id,
                "deleted_machine_hash": hash_val,
                "data_count_moved": data_count,
                "target_machine_hash": next_hash,
                "remaining_machines": len(self.machine_ids)
            }
        }
    
    def add_data(self, data_value):
        if not self.machines:
            return {
                "success": False,
                "message": "No machines available",
                "details": {
                    "data_value": data_value,
                    "action": "Failed - no machines to assign data"
                }
            }
        
        hash_val = self.get_hash(data_value)
        next_machine_hash = self.get_next_hash(hash_val)
        
        # Check if data already exists
        data_already_exists = (data_value, hash_val) in self.data_map[next_machine_hash]
        
        if not data_already_exists:
            self.data_map[next_machine_hash].add((data_value, hash_val))
        
        # Get current data count for the machine
        current_data_count = len(self.data_map[next_machine_hash])
        
        return {
            "success": True,
            "message": "Data added successfully" if not data_already_exists else "Data already exists",
            "details": {
                "data_value": data_value,
                "data_hash": hash_val,
                "machine_hash": next_machine_hash,
                "data_already_existed": data_already_exists,
                "current_data_count": current_data_count,
                "total_data_count": sum(len(items) for items in self.data_map.values())
            }
        }
    
    def delete_data(self, data_value):
        if not self.machines:
            return {"success": False, "message": "No machines available"}
        
        hash_val = self.get_hash(data_value)
        next_machine_hash = self.get_next_hash(hash_val)
        
        if next_machine_hash in self.data_map:
            # Check if data exists before deletion
            data_existed = (data_value, hash_val) in self.data_map[next_machine_hash]
            self.data_map[next_machine_hash].discard((data_value, hash_val))
            
            # Get current data count for the machine
            current_data_count = len(self.data_map[next_machine_hash])
            
            return {
                "success": True,
                "message": "Data deleted successfully",
                "details": {
                    "deleted_data_value": data_value,
                    "deleted_data_hash": hash_val,
                    "machine_hash": next_machine_hash,
                    "data_existed": data_existed,
                    "current_data_count": current_data_count,
                    "total_data_count": sum(len(items) for items in self.data_map.values())
                }
            }
        else:
            return {
                "success": False,
                "message": "Machine not found",
                "details": {
                    "data_value": data_value,
                    "data_hash": hash_val,
                    "machine_hash": next_machine_hash
                }
            }
    
    def get_status(self):
        result = {
            "machine_count": len(self.machines),
            "machines": self.machines.copy(),
            "total_data": 0,
            "distribution": []
        }
        
        for machine_hash, data_set in self.data_map.items():
            result["total_data"] += len(data_set)
            # Convert tuples to lists for JSON serialization
            items_list = [list(item) for item in data_set]
            result["distribution"].append({
                "machine_hash": machine_hash,
                "item_count": len(data_set),
                "items": items_list
            })
        
        return result

# Create global instance
consistent_hash = ConsistentHash()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def api_status():
    return jsonify(consistent_hash.get_status())

@app.route('/api/machine', methods=['POST'])
def api_add_machine():
    data = request.get_json()
    if 'id' not in data:
        return jsonify({"success": False, "message": "Machine ID is required"}), 400
    return jsonify(consistent_hash.add_machine(data['id']))

@app.route('/api/machine/<int:machine_id>', methods=['DELETE'])
def api_delete_machine(machine_id):
    return jsonify(consistent_hash.delete_machine(machine_id))

@app.route('/api/data', methods=['POST'])
def api_add_data():
    data = request.get_json()
    if 'value' not in data:
        return jsonify({"success": False, "message": "Data value is required"}), 400
    return jsonify(consistent_hash.add_data(data['value']))

@app.route('/api/data/<int:data_value>', methods=['DELETE'])
def api_delete_data(data_value):
    return jsonify(consistent_hash.delete_data(data_value))

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=500)