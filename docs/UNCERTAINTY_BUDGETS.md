# IMUCA — Uncertainty Budgets and Source Allocation

## 1. Overview

In accordance with JCGM 100:2008 (GUM), an uncertainty budget explicitly tabulates all identified contributions affecting the measurement result, their probability distributions, standard uncertainties, sensitivity coefficients, and resulting variance shares.

This document formalizes the budgets for:
1. DC Voltage
2. DC Current (Indirect Shunt Resistor Model)
3. Temperature (Digital Sensor Model)

---

## 2. DC Voltage Uncertainty Budget

Nominal Operating Point: $5.000\text{ V}$ DC

| Index | Contributor Name | Source / Justification | Evaluation Type | Distribution | Input Value | Divisor | Standard Uncertainty $u_i$ | Sens. Coeff. $c_i$ | Uncertainty Contrib. $c_i u_i$ | Variance Share % | Degrees of Freedom $\nu_i$ |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | **Repeatability** | $n=10$ repeated observations | Type A | Normal | $s = 0.50\text{ mV}$ | $\sqrt{10}$ | $0.158\text{ mV}$ | $1.0$ | $0.158\text{ mV}$ | $0.27\%$ | $9$ |
| 2 | **ADC Resolution** | Least Significant Bit ($\Delta = 1\text{ mV}$) | Type B | Rectangular | $0.001\text{ V}$ | $\sqrt{3}$ | $0.577\text{ mV}$ | $1.0$ | $0.577\text{ mV}$ | $3.65\%$ | $\infty$ |
| 3 | **DUT Specification** | Manufacturer gain/offset tolerance ($0.1\%$) | Type B | Rectangular | $5.00\text{ mV}$ | $\sqrt{3}$ | $2.887\text{ mV}$ | $1.0$ | $2.887\text{ mV}$ | $91.24\%$ | $\infty$ |
| 4 | **Reference Standard** | Calibrated reference instrument uncertainty | Type B | Normal ($k=2$) | $1.00\text{ mV}$ | $2.0$ | $0.500\text{ mV}$ | $1.0$ | $0.500\text{ mV}$ | $2.74\%$ | $50$ |
| 5 | **Ambient Temperature** | Tempco drift ($50\ \mu\text{V/}^\circ\text{C} \times 10^\circ\text{C}$) | Type B | Rectangular | $0.50\text{ mV}$ | $\sqrt{3}$ | $0.289\text{ mV}$ | $1.0$ | $0.289\text{ mV}$ | $0.91\%$ | $\infty$ |

### Voltage Budget Summary
- **Combined Standard Uncertainty $u_c(V)$**:
  $$u_c = \sqrt{0.158^2 + 0.577^2 + 2.887^2 + 0.500^2 + 0.289^2} = 3.023\text{ mV}$$
- **Effective Degrees of Freedom $\nu_{eff}$**: $> 500$
- **Coverage Factor**: $k = 2.00$ ($95.45\%$ normal confidence)
- **Expanded Uncertainty $U(V)$**:
  $$U = 2.00 \times 3.023\text{ mV} = 6.046\text{ mV}$$
- **Reported Result**:
  $$(5.0000 \pm 0.0061)\text{ V} \quad (k=2.00, 95\% \text{ confidence})$$

---

## 3. DC Current Uncertainty Budget (Indirect Shunt Model)

Nominal Operating Point: $I = 1000.0\text{ mA}$ ($1.000\text{ A}$), $R_{shunt} = 0.100\ \Omega$, $V_{shunt} = 0.100\text{ V}$

| Index | Contributor Name | Source / Justification | Evaluation Type | Distribution | Input Value | Divisor | Standard Uncertainty $u_i$ | Sens. Coeff. $c_i$ | Uncertainty Contrib. $c_i u_i$ | Variance Share % | Degrees of Freedom $\nu_i$ |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | **Repeatability** | Repeated current readings ($n=10$) | Type A | Normal | $s = 0.50\text{ mA}$ | $\sqrt{10}$ | $0.158\text{ mA}$ | $1.0$ | $0.158\text{ mA}$ | $0.10\%$ | $9$ |
| 2 | **Shunt Voltage Drop** | Diff. ADC input noise & spec ($0.05\text{ mV}$) | Type B | Normal ($k=2$) | $0.05\text{ mV}$ | $2.0$ | $0.025\text{ mV}$ | $10.0\text{ A/V}$ | $0.250\text{ mA}$ | $0.25\%$ | $\infty$ |
| 3 | **Shunt Resistor Tolerance** | Resistor calibration tolerance ($0.5\%$ of $0.1\ \Omega$) | Type B | Rectangular | $0.50\text{ m}\Omega$ | $\sqrt{3}$ | $0.289\text{ m}\Omega$ | $-10.0\text{ A/}\Omega$ | $2.887\text{ mA}$ | $33.15\%$ | $\infty$ |
| 4 | **Shunt Tempco Effect** | Resistor TCR ($50\text{ ppm/}^\circ\text{C} \times 20^\circ\text{C}$) | Type B | Rectangular | $1.00\text{ m}\Omega$ | $\sqrt{3}$ | $0.577\text{ m}\Omega$ | $-10.0\text{ A/}\Omega$ | $5.774\text{ mA}$ | $66.30\%$ | $\infty$ |
| 5 | **Reference Current Meter** | Calibrated ammeter standard | Type B | Normal ($k=2$) | $0.50\text{ mA}$ | $2.0$ | $0.250\text{ mA}$ | $1.0$ | $0.250\text{ mA}$ | $0.25\%$ | $40$ |

### Current Budget Summary
- **Combined Standard Uncertainty $u_c(I)$**:
  $$u_c = \sqrt{0.158^2 + 0.250^2 + 2.887^2 + 5.774^2 + 0.250^2} = 6.463\text{ mA}$$
- **Expanded Uncertainty $U(I)$**:
  $$U = 2.00 \times 6.463\text{ mA} = 12.93\text{ mA} \approx 13\text{ mA}$$
- **Reported Result**:
  $$(1000 \pm 13)\text{ mA} \quad (k=2.00, 95\% \text{ confidence})$$

---

## 4. Temperature Uncertainty Budget (DS18B20 Digital Sensor)

Nominal Operating Point: $45.0\ ^\circ\text{C}$

| Index | Contributor Name | Source / Justification | Evaluation Type | Distribution | Input Value | Divisor | Standard Uncertainty $u_i$ | Sens. Coeff. $c_i$ | Uncertainty Contrib. $c_i u_i$ | Variance Share % | Degrees of Freedom $\nu_i$ |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | **12-bit Quantization** | LSB resolution ($0.0625\ ^\circ\text{C}$) | Type B | Rectangular | $0.0625\ ^\circ\text{C}$ | $\sqrt{3}$ | $0.036\ ^\circ\text{C}$ | $1.0$ | $0.036\ ^\circ\text{C}$ | $1.9\%$ | $\infty$ |
| 2 | **Factory Accuracy Spec** | Maxim datasheet spec ($\pm 0.5\ ^\circ\text{C}$) | Type B | Normal ($k=2$) | $0.50\ ^\circ\text{C}$ | $2.0$ | $0.250\ ^\circ\text{C}$ | $1.0$ | $0.250\ ^\circ\text{C}$ | $92.5\%$ | $\infty$ |
| 3 | **Self-Heating Dissipation** | Internal dissipation in active conversion | Type B | Rectangular | $0.08\ ^\circ\text{C}$ | $\sqrt{3}$ | $0.046\ ^\circ\text{C}$ | $1.0$ | $0.046\ ^\circ\text{C}$ | $3.1\%$ | $\infty$ |
| 4 | **Thermal Gradient Coupling** | Sensor-to-ambient thermal resistance | Type B | Triangular | $0.10\ ^\circ\text{C}$ | $\sqrt{6}$ | $0.041\ ^\circ\text{C}$ | $1.0$ | $0.041\ ^\circ\text{C}$ | $2.5\%$ | $\infty$ |

### Temperature Budget Summary
- **Combined Standard Uncertainty $u_c(T)$**:
  $$u_c = \sqrt{0.036^2 + 0.250^2 + 0.046^2 + 0.041^2} = 0.260\ ^\circ\text{C}$$
- **Expanded Uncertainty $U(T)$**:
  $$U = 2.00 \times 0.260\ ^\circ\text{C} = 0.520\ ^\circ\text{C}$$
- **Reported Result**:
  $$(45.00 \pm 0.52)\ ^\circ\text{C} \quad (k=2.00, 95\% \text{ confidence})$$

---

## 5. Identified Unknowns Requiring Physical Hardware Characterization

The following parameters cannot be fabricated or inferred from datasheets and must be determined experimentally during physical hardware testing:
1. **INA219 Internal PGA Non-Linearity**: Residual non-linearity across the 4 programmable gain ranges ($\pm 40\text{ mV}, \pm 80\text{ mV}, \pm 160\text{ mV}, \pm 320\text{ mV}$).
2. **Thermal Resistance of Assembled Shunt**: Real-world junction-to-ambient thermal impedance of the shunt resistor mounted on the PCB under continuous full-load current ($3.2\text{ A}$).
3. **Thermoelectric EMF (Seebeck Effect)**: Parasitic voltages developed across soldered copper-manganin shunt junctions under thermal gradients.
4. **DS18B20 Immersion Stem Conduction**: Heat sinking along probe leads in immersion versus ambient air installations.
