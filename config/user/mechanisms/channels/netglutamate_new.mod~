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
	POINT_PROCESS glutamate_syn_old
	NONSPECIFIC_CURRENT inmda,iampa
	RANGE gampamax,gnmdamax,inmda,iampa
	RANGE decayampa,dampa,taudampa
    RANGE decaynmda,dnmda,taudnmda
    RANGE facilampa,fampa,taufampa
    RANGE facilnmda,fnmda,taufnmda
	RANGE gnmda,gampa
	RANGE e,tau1,tau2,tau3,tau4
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
}

ASSIGNED { 
	inmda		(nA)  
	iampa		(nA)  
	gnmda		(nS)
	gampa		(nS)
	factor1		: NMDA normalization factor
	factor2		: AMPA normalization factor

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
}    

BREAKPOINT {  
    
	LOCAL count
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
	gampamax = weight_ampa
	gnmdamax = weight_nmda
	
	state_discontinuity( A, A+ factor1*gnmdamax*dnmda*fnmda)
	state_discontinuity( B, B+ factor1*gnmdamax*dnmda*fnmda)
	state_discontinuity( C, C+ factor2*gampamax*dampa*fampa)
	state_discontinuity( D, D+ factor2*gampamax*dampa*fampa)
	:state_discontinuity( gampa, gampa+ gampamax*dampa)
	state_discontinuity( dampa, dampa* decayampa)
	state_discontinuity( dnmda, dnmda* decaynmda)
    state_discontinuity( fampa, fampa + facilampa)
    state_discontinuity( fnmda, fnmda + facilnmda)
	
	VERBATIM
	/*
	printf("***********\n");
	printf("A = %.2f\n", A);
	printf("B = %.2f\n", B);
	printf("C = %.2f\n", C);
	printf("D = %.2f\n", D);
	*/
	ENDVERBATIM
}
DERIVATIVE state {
	A'=-A/tau1
	B'=-B/tau2
	C'=-C/tau3
	D'=-D/tau4
	dampa'=(1-dampa)/taudampa
	dnmda'=(1-dnmda)/taudnmda
    fampa'=(1-fampa)/taufampa
    fnmda'=(1-fnmda)/taufnmda
}





