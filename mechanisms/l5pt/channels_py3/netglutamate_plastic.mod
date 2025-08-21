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

	RANGE plasticity_trace
	RANGE ca_trace, calcium_tau
	RANGE total_ca_current, last_total_ca_current
	RANGE dend_ca_current, syn_ca_current

	RANGE depression_threshold, sad
	RANGE potentiation_threshold, happy
	RANGE nml_threshold, neutral

	RANGE depression_rate, potentiation_rate
	RANGE lr

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

	total_ca_current
	last_total_ca_current
	dend_ca_current
	syn_ca_current

	lr
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

	plasticity_trace
	ca_trace
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

	plasticity_trace = 1
	ca_trace = 0
	total_ca_current = 0
	last_total_ca_current = 0
	dend_ca_current = 0
	syn_ca_current = 0

	lr = 0
	sad = 0
	happy = 0
	neutral = 0

	: Register thresholds
	net_send(0, 1)
}    

BREAKPOINT {
	LOCAL count

	lr = learning_rate(ca_trace)

	dend_ca_current = fabs(ica_HVA + ica_LVA)
	syn_ca_current = fabs(inmda)
	total_ca_current = dend_ca_current + syn_ca_current

	SOLVE state METHOD cnexp

	gnmda=(A-B)/(1+n*exp(-gama*v) )
	gampa=(C-D)
	inmda =(1e-3)*gnmda*(v-e)
	iampa= (1e-3)*gampa*(v- e)
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
	A' = -A / tau1
    B' = -B / tau2
    C' = -C / tau3
    D' = -D / tau4
    dampa' = (1 - dampa) / taudampa
    dnmda' = (1 - dnmda) / taudnmda
    fampa' = (1 - fampa) / taufampa
    fnmda' = (1 - fnmda) / taufnmda

	if (sad == 1) {
		plasticity_trace' = -lr * (plasticity_trace - 0.5)
	}
	else if (happy == 1) {
		plasticity_trace' = lr * (3 - plasticity_trace)
	}
	else if (neutral == 1) {
		plasticity_trace' = 0
	}
	else {
		plasticity_trace' = 0
	}
	plasticity_trace' = plasticity_trace' * dt

	if (total_ca_current - last_total_ca_current > (1e-5)) {
        ca_trace' = (total_ca_current - last_total_ca_current) / dt  : add increase instantly
    } else {
        ca_trace' = -ca_trace / calcium_tau          : decay otherwise
    }

	last_total_ca_current = total_ca_current
}

FUNCTION learning_rate(x) {
    UNITSOFF

    : --- Transition 1: from baseline to max depression rate ---
    x_start = depression_threshold
    x_end = depression_threshold + ((nml_threshold - depression_threshold) / 2)
    y_start = 0.0
    y_end   = depression_rate
    k       = 2000

	: --- Baseline value ---
	learning_rate = 0.0

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
    y_start = depression_rate
    y_end   = 0.0
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
    y_start = 0.0
    y_end   = potentiation_rate
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
