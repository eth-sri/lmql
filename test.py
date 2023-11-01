def f():
    a = list(range(10))

    return a

def g():
    r = f()

    return r*2

print(g())