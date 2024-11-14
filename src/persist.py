import json
import os
import tempfile

class PersistentDict:
    def __init__(self, filepath):
        self.filepath = filepath
        # Ensure the file exists
        if not os.path.exists(self.filepath):
            self._write_to_file({})

    def _read_from_file(self):
        with open(self.filepath, 'r') as f:
            return json.load(f)

    def _write_to_file(self, data):
        # Create a temporary file and write JSON data
        with tempfile.NamedTemporaryFile('w', delete=False) as temp_file:
            json.dump(data, temp_file, indent=4)
            temp_file.flush()
        # Rename temp file to target file path
        os.sync()
        os.replace(temp_file.name, self.filepath)

    def __getitem__(self, key):
        data = self._read_from_file()
        return data[key]

    def __setitem__(self, key, value):
        data = self._read_from_file()
        data[key] = value
        self._write_to_file(data)

    def __delitem__(self, key):
        data = self._read_from_file()
        if key in data:
            del data[key]
            self._write_to_file(data)
        else:
            raise KeyError(f"Key '{key}' not found in the dictionary.")

    def __contains__(self, key):
        data = self._read_from_file()
        return key in data

    def __len__(self):
        data = self._read_from_file()
        return len(data)

    def __iter__(self):
        data = self._read_from_file()
        return iter(data)

    def items(self):
        data = self._read_from_file()
        return data.items()

    def keys(self):
        data = self._read_from_file()
        return data.keys()

    def values(self):
        data = self._read_from_file()
        return data.values()

    def get(self, key, default=None):
        data = self._read_from_file()
        return data.get(key, default)

    def clear(self):
        self._write_to_file({})
