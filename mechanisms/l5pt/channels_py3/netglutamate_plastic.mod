COMMENT
//****************************//
// Created by Alon Polsky 	//
//    apmega@yahoo.com		//
//		2010			//
//****************************//
Modified 2015 by Robert Egger
to include facilitation variable
as modeled by Varela et al. 1997
ENDCOMMENT

TITLE NMDA synapse with depression


NEURON {
	POINT_PROCESS glutamate_syn_plastic
	NONSPECIFIC_CURRENT inmda,iampa
	RANGE gampamax,gnmdamax,inmda,iampa
	RANGE decayampa,dampa,taudampa
    RANGE decaynmda,dnmda,taudnmda
    RANGE facilampa,fampa,taufampa
    RANGE facilnmda,fnmda,taufnmda
	RANGE gnmda,gampa
	RANGE e,tau1,tau2,tau3,tau4
	RANGE plasticity_trace, plasticity_tau
	RANGE dend_ca_trace, syn_ca_trace, ca_trace, last_ca_trace, ca_is_increasing
	RANGE calcium_tau, rmp
	RANGE abs_dend_ca_current, last_abs_dend_ca_current
	RANGE abs_syn_ca_current, last_abs_syn_ca_current
	RANGE happy_trace, neutral_trace, sad_trace
	RANGE potentiation_trace, potentiation_trace_bar, potentiation_trace_lp, depression_trace, depression_trace_bar, depression_trace_lp
	RANGE depression_threshold, sad
	RANGE potentiation_threshold, happy
	RANGE nml_threshold, neutral
	:RANGE depression_rate, potentiation_rate
	POINTER ica_HVA, ica_LVA
}

UNITS {
	(nA) 	= (nanoamp)
	(mV)	= (millivolt)
	(nS) 	= (nanomho)
	(mM)    = (milli/liter)
 	(mA) = (milliamp)
	(um) = (micron)
}

PARAMETER {
	gnmdamax=1	(nS)
	gampamax=1	(nS)
	e= 0.0	(mV)
	tau1=50	(ms)	: NMDA inactivation
	tau2=2	(ms)	: NMDA activation
	tau3=2	(ms)	: AMPA inactivation
	tau4=0.1	(ms)	: AMPA activation
	tau_ampa=2	(ms)	
	n=0.25 	(/mM)	    : Schiller and Larkum
	gama=0.08 	(/mV)   : Schiller and Larkum
	:n=0.28      (/mM)   : Jahr and Stevens
	:gama=0.062  (/mV)   : Jahr and Stevens
	dt 		(ms)
	v		(mV)
	decayampa=.5
	decaynmda=.5
	taudampa=200	(ms):tau decay
	taudnmda=200	(ms):tau decay
    taufampa=200    (ms)
    facilampa=0.0
    taufnmda=200    (ms)
    facilnmda=0.0

	plasticity_tau = 70 (s)
	calcium_tau = 10 (ms)

	depression_threshold = 0.005
	depression_rate = 0.0001
	potentiation_threshold = 0.02
	potentiation_rate = 0.0005
	nml_threshold = 0.015
}

ASSIGNED { 
	inmda		(nA)  
	iampa		(nA)  
	gnmda		(nS)
	gampa		(nS)
	factor1		: NMDA normalization factor
	factor2		: AMPA normalization factor

	ca_trace
	last_ca_trace
	ca_is_increasing
	abs_dend_ca_current
	last_abs_dend_ca_current
	abs_syn_ca_current
	last_abs_syn_ca_current
	happy_trace
	neutral_trace
	sad_trace
	sad
	happy
	neutral
	ica_HVA
	ica_LVA

	x0
	val_start
	val_end
	norm
    x_start
	x_end
	y_start
	y_end
	k
}

STATE {
	A 		(nS)
	B 		(nS)
	C 		(nS)
	D 		(nS)
	dampa
	dnmda
    fampa
    fnmda

	dend_ca_trace
	syn_ca_trace
	plasticity_trace
	potentiation_trace
	potentiation_trace_bar
	potentiation_trace_lp
	depression_trace
	depression_trace_bar
	depression_trace_lp
}


INITIAL {
	LOCAL tp1, tp2
    gnmda=0 
    gampa=0 
	A=0
	B=0
	C=0
	D=0
	dampa=1
	dnmda=1
    fampa=1
    fnmda=1
	
	tp1 = (tau2*tau1)/(tau1 - tau2) * log(tau1/tau2)
	factor1 = -exp(-tp1/tau2) + exp(-tp1/tau1)
	factor1 = 1/factor1
	
	tp2 = (tau4*tau3)/(tau3 - tau4) * log(tau3/tau4)
	factor2 = -exp(-tp2/tau4) + exp(-tp2/tau3)
	factor2 = 1/factor2

	dend_ca_trace = 0
	syn_ca_trace = 0
	ca_trace = 0
	last_ca_trace = ca_trace
	ca_is_increasing = 0
	plasticity_trace = 0.5
	abs_dend_ca_current = 0
	last_abs_dend_ca_current = abs_dend_ca_current
	abs_syn_ca_current = 0
	last_abs_syn_ca_current = abs_syn_ca_current
	happy_trace = 0
	neutral_trace = 0
	sad_trace = 0
	potentiation_trace = 0
	potentiation_trace_bar = 0
	potentiation_trace_lp = 0
	depression_trace = 0
	depression_trace_bar = 0
	depression_trace_lp = 0
	sad = 0
	happy = 0
	neutral = 0

	net_send(0, 1)
}    

BREAKPOINT {
	LOCAL count

	abs_dend_ca_current = fabs(ica_HVA + ica_LVA)
	abs_syn_ca_current = fabs(inmda)

	SOLVE state METHOD cnexp

	gnmda=(A-B)/(1+n*exp(-gama*v) )
	gampa=(C-D)
	inmda =(1e-3)*gnmda*(v-e)
	iampa= (1e-3)*gampa*(v- e)

	:ca_trace = abs_syn_ca_current + abs_dend_ca_current
	ca_trace = syn_ca_trace + dend_ca_trace
	: dend_ca_trace = dend_ca_trace + (rmp - dend_ca_trace) / calcium_tau * dt
}

NET_RECEIVE(weight_ampa, weight_nmda) {
    INITIAL {
        gampamax = weight_ampa
        gnmdamax = weight_nmda
    }

	if (flag == 1) {
		WATCH (ca_trace > depression_threshold) 2
		WATCH (ca_trace < depression_threshold) 3
		WATCH (ca_trace > potentiation_threshold) 4
		WATCH (ca_trace < potentiation_threshold) 5
		WATCH (ca_trace > nml_threshold) 6
		WATCH (ca_trace < nml_threshold) 7
	}

	if (flag == 0) {
		: Presynaptic spike

		gampamax = gampamax
		gnmdamax = weight_nmda

		: Normal dynamics
		A = A + factor1 * gnmdamax * dnmda * fnmda
		B = B + factor1 * gnmdamax * dnmda * fnmda
		C = C + factor2 * gampamax * dampa * fampa
		D = D + factor2 * gampamax * dampa * fampa

		dampa = dampa * decayampa
		dnmda = dnmda * decaynmda
		fampa = fampa + facilampa
		fnmda = fnmda + facilnmda
	}

	else if (flag == 2) {
		sad = 1
	}
	else if (flag == 3) {
		sad = 0
	}
	else if (flag == 4) {
		happy = 1
		neutral = 0
	}
	else if (flag == 5) {
		happy = 0
		neutral = 1
	}
	else if (flag == 6) {
		neutral = 1
		sad = 0
	}
	else if (flag == 7) {
		neutral = 0
		sad = 1
	}
}

DERIVATIVE state {
	LOCAL lr, potentiation_trace_smooth
	lr = learning_rate(ca_trace)

	A' = -A / tau1
    B' = -B / tau2
    C' = -C / tau3
    D' = -D / tau4
    dampa' = (1 - dampa) / taudampa
    dnmda' = (1 - dnmda) / taudnmda
    fampa' = (1 - fampa) / taufampa
    fnmda' = (1 - fnmda) / taufnmda

	if (ca_trace - last_ca_trace > (1e-5)) {
		ca_is_increasing = 1

		potentiation_trace = 0
		depression_trace = 0
	}
	else {
		if (ca_is_increasing == 1) {
			: Peak occured
			if (sad == 1) {
				depression_trace = -lr
				potentiation_trace = 0
			}
			else if (happy == 1) {
				potentiation_trace = lr
				depression_trace = 0
			}
			else {
				potentiation_trace = 0
				depression_trace = 0
			}
		}
		else {
			potentiation_trace = 0
			depression_trace = 0
		}
		ca_is_increasing = 0
	}
	last_ca_trace = ca_trace

	if (potentiation_trace > potentiation_trace_lp) {
		potentiation_trace_lp' = (potentiation_trace - potentiation_trace_lp) / 1  : rise quickly
	} else {
		potentiation_trace_lp' = (potentiation_trace - potentiation_trace_lp) / 500  : decay slowly
	}
	:potentiation_trace_bar' = (potentiation_trace - potentiation_trace_bar) / 10
	:potentiation_trace_smooth = sigmoid_sat(1.7, (potentiation_trace_bar * 1000))
	:potentiation_trace_lp' = (potentiation_trace_smooth - potentiation_trace_lp) / 500

	if (sad == 1) {
		plasticity_trace' = -lr * plasticity_trace
	}
	else if (happy == 1) {
		plasticity_trace' = lr * (1 - plasticity_trace)
	}
	else if (neutral == 1) {
		plasticity_trace' = 0
	}
	else {
		if (plasticity_trace > 0.6) {
			plasticity_trace' = 0.00001 * (1 - plasticity_trace)
		}
		else if (plasticity_trace < 0.6 && plasticity_trace > 0.5) {
			plasticity_trace' = 0.00001 * (0.5 - plasticity_trace)
		}
		else if (plasticity_trace > 0.4 && plasticity_trace < 0.5) {
			plasticity_trace' = 0.00001 * (0.5 - plasticity_trace)
		}
		else if (plasticity_trace < 0.4) {
			plasticity_trace' = -0.00001 * plasticity_trace
		}
		else if (plasticity_trace == 0.5) {
			plasticity_trace' = 0
		}
	}

	plasticity_trace' = plasticity_trace' * dt

	if (abs_dend_ca_current - last_abs_dend_ca_current > (1e-5)) {
        dend_ca_trace' = (abs_dend_ca_current - last_abs_dend_ca_current) / dt  : add increase instantly
    } else {
        dend_ca_trace' = -dend_ca_trace / calcium_tau          : decay otherwise
    }
	:dend_ca_trace' = (dend_ca_trace - dend_ca_trace) / 2  : low-pass filter

	if (abs_syn_ca_current - last_abs_syn_ca_current > (1e-5)) {
		syn_ca_trace' = (abs_syn_ca_current - last_abs_syn_ca_current) / dt  : add increase instantly
    } else {
        syn_ca_trace' = -syn_ca_trace / calcium_tau          : decay otherwise

		happy_trace = 0
		neutral_trace = 0
		sad_trace = 0
    }
	:syn_ca_trace' = (syn_ca_trace - syn_ca_trace) / 2  : low-pass filter

	:potentiation_trace_bar' = (happy_trace - potentiation_trace_bar) / 10
	:potentiation_trace_lp = sigmoid_sat(1.7, (potentiation_trace_bar * 1000))
	:potentiation_trace' = (potentiation_trace_lp - potentiation_trace) / 500
	:depression_trace_bar' = (sad_trace - depression_trace_bar) / 10
	:depression_trace_lp = sigmoid_sat(1.7, (depression_trace_bar * 200))
	:depression_trace' = (depression_trace_lp - depression_trace) / 500

	last_abs_dend_ca_current = abs_dend_ca_current
	last_abs_syn_ca_current = abs_syn_ca_current
}

FUNCTION sigmoid_sat(slope, value) {	: sigmoidal saturation
	sigmoid_sat = 2.0 / (1.0 + pow(slope, -value)) - 1.0
}

FUNCTION learning_rate(x) {
    UNITSOFF

    : --- Transition 1: from baseline to max depression rate ---
    x_start = depression_threshold
    x_end = depression_threshold + ((nml_threshold - depression_threshold) / 2)
    y_start = 0.00001
    y_end   = 0.0001
    k       = 2000

	: --- Baseline value ---
	learning_rate = 0.00001

    if (x >= x_start && x <= x_end) {
        x0 = (x_start + x_end) / 2
        val_start = 1 / (1 + exp(-k * (x_start - x0)))
        val_end   = 1 / (1 + exp(-k * (x_end - x0)))
        norm = (1 / (1 + exp(-k * (x - x0))) - val_start) / (val_end - val_start)
        if (norm < 0) { norm = 0 }
        if (norm > 1) { norm = 1 }
        learning_rate = y_start + (y_end - y_start) * norm
        :UNITSON
    }

    : --- Transition 2: from max depression rate to baseline ---
    x_start = depression_threshold + ((nml_threshold - depression_threshold) / 2)
    x_end = nml_threshold
    y_start = 0.0001
    y_end   = 0.00001
    k       = 2000

    if (x >= x_start && x <= x_end) {
        x0 = (x_start + x_end) / 2
        val_start = 1 / (1 + exp(-k * (x_start - x0)))
        val_end   = 1 / (1 + exp(-k * (x_end - x0)))
        norm = (1 / (1 + exp(-k * (x - x0))) - val_start) / (val_end - val_start)
        if (norm < 0) { norm = 0 }
        if (norm > 1) { norm = 1 }
        learning_rate = y_start + (y_end - y_start) * norm
        :UNITSON
    }

    : --- Transition 3: from baseline to max potentiation rate ---
    x_start = potentiation_threshold
    x_end = 0.03
    y_start = 0.00001
    y_end   = 0.0005
    k       = 2000

	if (x >= x_start) {
		learning_rate = y_end
	}

    :if (x >= x_start && x <= x_end) {
        :x0 = (x_start + x_end) / 2
        :val_start = 1 / (1 + exp(-k * (x_start - x0)))
        :val_end   = 1 / (1 + exp(-k * (x_end - x0)))
        :norm = (1 / (1 + exp(-k * (x - x0))) - val_start) / (val_end - val_start)
        :if (norm < 0) { norm = 0 }
        :if (norm > 1) { norm = 1 }
        :learning_rate = y_start + (y_end - y_start) * norm
        :UNITSON
    :} else if (x > x_end) {
		:learning_rate = y_end
	:}

    UNITSON
}
