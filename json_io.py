import json
import numpy as np




def convert_dict(data):
   '''Convert all numpy arrays in dict to lists.
   '''
   data_converted = {}
   for key, value in data.items():
      if isinstance(value, np.ndarray):
         data_converted[key] = value.tolist()
      else:
         data_converted[key] = value
   return data_converted


def recover_dict(data):
   '''Convert all lists in dict back to numpy arrays.
   '''
   for key, value in data.items():
      if isinstance(value, list):
         # For simplicity, we'll assume any list should be converted to a NumPy array
         data[key] = np.array(value)
      else:
         data[key] = value
   return data


def saveJson(param, path):
   # convert the numpy arrays to list inthe dict
   param_converted = convert_dict(param)

   # save all parameters and data
   with open(path, 'w') as f:
      json.dump(param_converted, f)
      #print('Saved json file')


def loadJson(path):
   # save all parameters and data
   with open(path, 'r') as f:
      param_loaded = json.load(f)

   # convert the lists back to numpy arrays
   param = recover_dict(param_loaded)
   #print('Loaded json file')

   return param





#####################################################
#####################################################
#####################################################

if __name__=="__main__":

   # Sample dictionary with mixed types
   param = {
       'int': 1,
       'float': 2.5,
       'str': 'example',
       'array_1d': np.array([1, 2, 3]),
       'array_2d': np.array([[1, 2], [3, 4]]),
   }
   print(param)

   # save it to json file
   path = './test_json_io.json'
   saveJson(param, path)

   # load the json file back
   param_read = loadJson(path)
   print(param_read)



