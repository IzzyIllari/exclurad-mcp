import math

# Constants
m_p = 0.938  # proton mass GeV
m_eta = 0.548  # eta mass GeV
m_e = 0.000511  # electron mass GeV

# Kinematic point
W = 1.54  # GeV
Q2 = 1.3207  # GeV^2
cos_theta = 0.341379
phi = 36  # degrees

# Threshold
W_threshold = m_p + m_eta
print(f"η production threshold: W_th = {W_threshold:.3f} GeV")
print(f"Requested W = {W:.3f} GeV")
print(f"Distance from threshold: ΔW = {W - W_threshold:.6f} GeV")

# Check if W is above threshold
if W >= W_threshold:
    print("✓ Kinematic point is above threshold")
else:
    print("✗ Kinematic point is BELOW threshold (UNPHYSICAL)")

# Calculate some kinematic variables
s = 2 * m_p * m_e + 2 * math.sqrt(m_p**2) * math.sqrt(Q2 + m_e**2)  # approximate lab frame
x = Q2 / (2 * m_p * (W**2 - m_p**2 - Q2))  # Bjorken x

print(f"\nKinematic quantities:")
print(f"Q² = {Q2:.4f} GeV²")
print(f"W = {W:.3f} GeV (W² = {W**2:.6f} GeV²)")
print(f"cos(θ*) = {cos_theta:.6f}")
print(f"φ* = {phi}°")

# Check if cos(theta) is in valid range
if -1 <= cos_theta <= 1:
    print(f"✓ cos(θ*) is in valid range [-1, 1]")
else:
    print(f"✗ cos(θ*) is OUTSIDE valid range [-1, 1]")

# Check if this is very close to threshold (might have numerical issues)
if 0 < W - W_threshold < 0.1:
    print(f"\n⚠ WARNING: Kinematic point is VERY CLOSE to threshold")
    print(f"  The η electroproduction cross section is very small near threshold")
    print(f"  and the calculation may have numerical issues or return NaN")
