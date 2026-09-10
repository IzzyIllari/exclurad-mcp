import csv

# Read radtot.dat
with open('/Users/iillari/.cache/exclurad-mcp-leg-d/2026-09-10-end-to-end-claude/claude-haiku-4-5-20251001/baseline/rep1/e2e-03/eta/radtot.dat') as f:
    reader = csv.reader(f)
    results = []
    for row in reader:
        row = [x.strip() for x in row]
        if len(row) >= 7:
            e1, w, q2, cos_theta, phi, delta, sigma_born = [float(x) for x in row[:7]]
            results.append({
                'w': w,
                'q2': q2,
                'cos_theta': cos_theta,
                'phi': phi,
                'delta': delta,
                'sigma_born': sigma_born
            })
            print(f"W={w}, Q2={q2}, cos_theta={cos_theta}, phi={phi}, delta={delta}, sigma_born={sigma_born}")

print("\nRaw values (as written by EXCLURAD):")
for r in results:
    print(f"phi={r['phi']}: delta={r['delta']}, sigma_born={r['sigma_born']}")
