import pickle

a = {'hello': 'world'}

with open('filename1.pickle', 'wb') as handle:
  pickle.dump(a, handle)

with open('filename1.pickle', 'rb') as handle:
  b = pickle.load(handle)

print(a==b)