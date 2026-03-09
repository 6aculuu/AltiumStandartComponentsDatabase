import numpy as np
from scipy.optimize import curve_fit

x = np.array([1, 2, 3, 4, 5, 6], float)
y = np.array([1, 1.8, 2.4, 2.8, 3, 3.1], float)

def logistic(x, L, k, x0, C):  # C + L/(1+exp(-k*(x-x0)))
    return C + L / (1 + np.exp(-k * (x - x0)))

# Стартовые параметры на основе данных
L0 = y.max() - y.min()       # ~2.1
C0 = y.min()                 # ~1.0
x0_0 = (x.min() + x.max())/2 # ~3.5
k0 = 1.0
p0 = [L0, k0, x0_0, C0]

params, _ = curve_fit(logistic, x, y, p0=p0, maxfev=50000)
L, k, x0, C = params
sse = np.sum((y - logistic(x, *params))**2)

print(f"f(x) = {C:.6f} + {L:.6f}/(1 + exp(-{k:.6f}*(x - {x0:.6f})))")
print(f"SSE = {sse:.9f}")
print(f"Асимптота = {C+L:.6f}")
