import pickle

a = {'hello': 'world'}

with open('filename5.pickle', 'wb') as handle:
  pickle.dump(a, handle)

with open('filename5.pickle', 'rb') as handle:
  b = pickle.load(handle)

print(a==b)