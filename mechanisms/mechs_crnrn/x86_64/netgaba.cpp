/* Created by Language version: 7.7.0 */
/* VECTORIZED */
#define NRN_VECTORIZED 1
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include "mech_api.h"
#undef PI
#define nil 0
#define _pval pval
#include "md1redef.h"
#include "section.h"
#include "nrniv_mf.h"
#include "md2redef.h"
 
#if !NRNGPU
#undef exp
#define exp hoc_Exp
#endif
 
#define nrn_init _nrn_init__gaba_syn
#define _nrn_initial _nrn_initial__gaba_syn
#define nrn_cur _nrn_cur__gaba_syn
#define _nrn_current _nrn_current__gaba_syn
#define nrn_jacob _nrn_jacob__gaba_syn
#define nrn_state _nrn_state__gaba_syn
#define _net_receive _net_receive__gaba_syn 
#define state state__gaba_syn 
 
#define _threadargscomma_ _p, _ppvar, _thread, _nt,
#define _threadargsprotocomma_ double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt,
#define _threadargs_ _p, _ppvar, _thread, _nt
#define _threadargsproto_ double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt
 	/*SUPPRESS 761*/
	/*SUPPRESS 762*/
	/*SUPPRESS 763*/
	/*SUPPRESS 765*/
	 extern double *hoc_getarg(int);
 /* Thread safe. No static _p or _ppvar. */
 
#define t _nt->_t
#define dt _nt->_dt
#define e _p[0]
#define e_columnindex 0
#define risetime _p[1]
#define risetime_columnindex 1
#define decaytime _p[2]
#define decaytime_columnindex 2
#define taudgaba _p[3]
#define taudgaba_columnindex 3
#define decaygaba _p[4]
#define decaygaba_columnindex 4
#define taufgaba _p[5]
#define taufgaba_columnindex 5
#define facilgaba _p[6]
#define facilgaba_columnindex 6
#define i _p[7]
#define i_columnindex 7
#define ggaba _p[8]
#define ggaba_columnindex 8
#define dgaba _p[9]
#define dgaba_columnindex 9
#define fgaba _p[10]
#define fgaba_columnindex 10
#define R _p[11]
#define R_columnindex 11
#define D _p[12]
#define D_columnindex 12
#define factor _p[13]
#define factor_columnindex 13
#define Ddgaba _p[14]
#define Ddgaba_columnindex 14
#define Dfgaba _p[15]
#define Dfgaba_columnindex 15
#define DR _p[16]
#define DR_columnindex 16
#define DD _p[17]
#define DD_columnindex 17
#define v _p[18]
#define v_columnindex 18
#define _g _p[19]
#define _g_columnindex 19
#define _tsav _p[20]
#define _tsav_columnindex 20
#define _nd_area  *_ppvar[0].get<double*>()
 
#if MAC
#if !defined(v)
#define v _mlhv
#endif
#if !defined(h)
#define h _mlhh
#endif
#endif
 static int hoc_nrnpointerindex =  -1;
 static Datum* _extcall_thread;
 static Prop* _extcall_prop;
 /* external NEURON variables */
 /* declaration of user functions */
 static int _mechtype;
extern void _nrn_cacheloop_reg(int, int);
extern void hoc_register_prop_size(int, int, int);
extern void hoc_register_limits(int, HocParmLimits*);
extern void hoc_register_units(int, HocParmUnits*);
extern void nrn_promote(Prop*, int, int);
extern Memb_func* memb_func;
 
#define NMODL_TEXT 1
#if NMODL_TEXT
static void register_nmodl_text_and_filename(int mechtype);
#endif
 extern Prop* nrn_point_prop_;
 static int _pointtype;
 static void* _hoc_create_pnt(Object* _ho) { void* create_point_process(int, Object*);
 return create_point_process(_pointtype, _ho);
}
 static void _hoc_destroy_pnt(void*);
 static double _hoc_loc_pnt(void* _vptr) {double loc_point_process(int, void*);
 return loc_point_process(_pointtype, _vptr);
}
 static double _hoc_has_loc(void* _vptr) {double has_loc_point(void*);
 return has_loc_point(_vptr);
}
 static double _hoc_get_loc_pnt(void* _vptr) {
 double get_loc_point_process(void*); return (get_loc_point_process(_vptr));
}
 extern void _nrn_setdata_reg(int, void(*)(Prop*));
 static void _setdata(Prop* _prop) {
 _extcall_prop = _prop;
 }
 static void _hoc_setdata(void* _vptr) { Prop* _prop;
 _prop = ((Point_process*)_vptr)->_prop;
   _setdata(_prop);
 }
 /* connect user functions to hoc names */
 static VoidFunc hoc_intfunc[] = {
 {0, 0}
};
 static Member_func _member_func[] = {
 {"loc", _hoc_loc_pnt},
 {"has_loc", _hoc_has_loc},
 {"get_loc", _hoc_get_loc_pnt},
 {0, 0}
};
 /* declare global and static user variables */
 /* some parameters have upper and lower limits */
 static HocParmLimits _hoc_parm_limits[] = {
 {0, 0, 0}
};
 static HocParmUnits _hoc_parm_units[] = {
 {"e", "mV"},
 {"risetime", "ms"},
 {"decaytime", "ms"},
 {"taudgaba", "ms"},
 {"taufgaba", "ms"},
 {"i", "nA"},
 {0, 0}
};
 static double D0 = 0;
 static double R0 = 0;
 static double delta_t = 0.01;
 static double dgaba0 = 0;
 static double fgaba0 = 0;
 /* connect global user variables to hoc */
 static DoubScal hoc_scdoub[] = {
 {0, 0}
};
 static DoubVec hoc_vdoub[] = {
 {0, 0, 0}
};
 static double _sav_indep;
 static void nrn_alloc(Prop*);
static void  nrn_init(NrnThread*, Memb_list*, int);
static void nrn_state(NrnThread*, Memb_list*, int);
 static void nrn_cur(NrnThread*, Memb_list*, int);
static void  nrn_jacob(NrnThread*, Memb_list*, int);
 static void _hoc_destroy_pnt(void* _vptr) {
   destroy_point_process(_vptr);
}
 
static int _ode_count(int);
static void _ode_map(int, double**, double**, double*, Datum*, double*, int);
static void _ode_spec(NrnThread*, Memb_list*, int);
static void _ode_matsol(NrnThread*, Memb_list*, int);
 
#define _cvode_ieq _ppvar[2].literal_value<int>()
 static void _ode_matsol_instance1(_threadargsproto_);
 /* connect range variables in _p that hoc is supposed to know about */
 static const char *_mechanism[] = {
 "7.7.0",
"gaba_syn",
 "e",
 "risetime",
 "decaytime",
 "taudgaba",
 "decaygaba",
 "taufgaba",
 "facilgaba",
 0,
 "i",
 "ggaba",
 0,
 "dgaba",
 "fgaba",
 "R",
 "D",
 0,
 0};
 
extern Prop* need_memb(Symbol*);

static void nrn_alloc(Prop* _prop) {
	Prop *prop_ion;
	double *_p; Datum *_ppvar;
  if (nrn_point_prop_) {
	_prop->_alloc_seq = nrn_point_prop_->_alloc_seq;
	_p = nrn_point_prop_->param;
	_ppvar = nrn_point_prop_->dparam;
 }else{
 	_p = nrn_prop_data_alloc(_mechtype, 21, _prop);
 	/*initialize range parameters*/
 	e = -60;
 	risetime = 1;
 	decaytime = 20;
 	taudgaba = 200;
 	decaygaba = 0.8;
 	taufgaba = 200;
 	facilgaba = 0;
  }
 	_prop->param = _p;
 	_prop->param_size = 21;
  if (!nrn_point_prop_) {
 	_ppvar = nrn_prop_datum_alloc(_mechtype, 3, _prop);
  }
 	_prop->dparam = _ppvar;
 	/*connect ionic variables to this model*/
 
}
 static void _initlists();
  /* some states have an absolute tolerance */
 static Symbol** _atollist;
 static HocStateTolerance _hoc_state_tol[] = {
 {0, 0}
};
 static void _net_receive(Point_process*, double*, double);
 extern Symbol* hoc_lookup(const char*);
extern void _nrn_thread_reg(int, int, void(*)(Datum*));
extern void _nrn_thread_table_reg(int, void(*)(double*, Datum*, Datum*, NrnThread*, int));
extern void hoc_register_tolerance(int, HocStateTolerance*, Symbol***);
extern void _cvode_abstol( Symbol**, double*, int);

 extern "C" void _netgaba_reg() {
	int _vectorized = 1;
  _initlists();
 	_pointtype = point_register_mech(_mechanism,
	 nrn_alloc,nrn_cur, nrn_jacob, nrn_state, nrn_init,
	 hoc_nrnpointerindex, 1,
	 _hoc_create_pnt, _hoc_destroy_pnt, _member_func);
 _mechtype = nrn_get_mechtype(_mechanism[1]);
     _nrn_setdata_reg(_mechtype, _setdata);
 #if NMODL_TEXT
  register_nmodl_text_and_filename(_mechtype);
#endif
  hoc_register_prop_size(_mechtype, 21, 3);
  hoc_register_dparam_semantics(_mechtype, 0, "area");
  hoc_register_dparam_semantics(_mechtype, 1, "pntproc");
  hoc_register_dparam_semantics(_mechtype, 2, "cvodeieq");
 	hoc_register_cvode(_mechtype, _ode_count, _ode_map, _ode_spec, _ode_matsol);
 	hoc_register_tolerance(_mechtype, _hoc_state_tol, &_atollist);
 pnt_receive[_mechtype] = _net_receive;
 pnt_receive_size[_mechtype] = 1;
 	hoc_register_var(hoc_scdoub, hoc_vdoub, hoc_intfunc);
 	ivoc_help("help ?1 gaba_syn /gpfs/soma_fs/scratch/saka/project_src/in_silico_framework/mechanisms/channels_py3_wip/netgaba.mod\n");
 hoc_register_limits(_mechtype, _hoc_parm_limits);
 hoc_register_units(_mechtype, _hoc_parm_units);
 }
static int _reset;
static const char *modelname = "GABAA synapse activated by the network";

static int error;
static int _ninits = 0;
static int _match_recurse=1;
static void _modl_cleanup(){ _match_recurse=1;}
 
static int _ode_spec1(_threadargsproto_);
/*static int _ode_matsol1(_threadargsproto_);*/
 static int _slist1[4], _dlist1[4];
 static int state(_threadargsproto_);
 
static void _net_receive (Point_process* _pnt, double* _args, double _lflag) 
{  double* _p; Datum* _ppvar; Datum* _thread; NrnThread* _nt;
   _thread = (Datum*)0; _nt = (NrnThread*)_pnt->_vnt;   _p = _pnt->_prop->param; _ppvar = _pnt->_prop->dparam;
  if (_tsav > t){ hoc_execerror(hoc_object_name(_pnt->ob), ":Event arrived out of order. Must call ParallelContext.set_maxstep AFTER assigning minimum NetCon.delay");}
 _tsav = t; {
     if (nrn_netrec_state_adjust && !cvode_active_){
    /* discon state adjustment for cnexp case (rate uses no local variable) */
    double __state = R;
    double __primary = (R + factor * _args[0] * dgaba * fgaba) - __state;
     __primary += ( 1. - exp( 0.5*dt*( ( - 1.0 ) / risetime ) ) )*( - ( 0.0 ) / ( ( - 1.0 ) / risetime ) - __primary );
    R += __primary;
  } else {
 R = R + factor * _args[0] * dgaba * fgaba ;
     }
   if (nrn_netrec_state_adjust && !cvode_active_){
    /* discon state adjustment for cnexp case (rate uses no local variable) */
    double __state = D;
    double __primary = (D + factor * _args[0] * dgaba * fgaba) - __state;
     __primary += ( 1. - exp( 0.5*dt*( ( - 1.0 ) / decaytime ) ) )*( - ( 0.0 ) / ( ( - 1.0 ) / decaytime ) - __primary );
    D += __primary;
  } else {
 D = D + factor * _args[0] * dgaba * fgaba ;
     }
   if (nrn_netrec_state_adjust && !cvode_active_){
    /* discon state adjustment for cnexp case (rate uses no local variable) */
    double __state = dgaba;
    double __primary = (dgaba * decaygaba) - __state;
     __primary += ( 1. - exp( 0.5*dt*( ( ( ( - 1.0 ) ) ) / taudgaba ) ) )*( - ( ( ( 1.0 ) ) / taudgaba ) / ( ( ( ( - 1.0 ) ) ) / taudgaba ) - __primary );
    dgaba += __primary;
  } else {
 dgaba = dgaba * decaygaba ;
     }
   if (nrn_netrec_state_adjust && !cvode_active_){
    /* discon state adjustment for cnexp case (rate uses no local variable) */
    double __state = fgaba;
    double __primary = (fgaba + facilgaba) - __state;
     __primary += ( 1. - exp( 0.5*dt*( ( ( ( - 1.0 ) ) ) / taufgaba ) ) )*( - ( ( ( 1.0 ) ) / taufgaba ) / ( ( ( ( - 1.0 ) ) ) / taufgaba ) - __primary );
    fgaba += __primary;
  } else {
 fgaba = fgaba + facilgaba ;
     }
 } }
 
/*CVODE*/
 static int _ode_spec1 (double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt) {int _reset = 0; {
   DR = - R / risetime ;
   DD = - D / decaytime ;
   Ddgaba = ( 1.0 - dgaba ) / taudgaba ;
   Dfgaba = ( 1.0 - fgaba ) / taufgaba ;
   }
 return _reset;
}
 static int _ode_matsol1 (double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt) {
 DR = DR  / (1. - dt*( ( - 1.0 ) / risetime )) ;
 DD = DD  / (1. - dt*( ( - 1.0 ) / decaytime )) ;
 Ddgaba = Ddgaba  / (1. - dt*( ( ( ( - 1.0 ) ) ) / taudgaba )) ;
 Dfgaba = Dfgaba  / (1. - dt*( ( ( ( - 1.0 ) ) ) / taufgaba )) ;
  return 0;
}
 /*END CVODE*/
 static int state (double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt) { {
    R = R + (1. - exp(dt*(( - 1.0 ) / risetime)))*(- ( 0.0 ) / ( ( - 1.0 ) / risetime ) - R) ;
    D = D + (1. - exp(dt*(( - 1.0 ) / decaytime)))*(- ( 0.0 ) / ( ( - 1.0 ) / decaytime ) - D) ;
    dgaba = dgaba + (1. - exp(dt*(( ( ( - 1.0 ) ) ) / taudgaba)))*(- ( ( ( 1.0 ) ) / taudgaba ) / ( ( ( ( - 1.0 ) ) ) / taudgaba ) - dgaba) ;
    fgaba = fgaba + (1. - exp(dt*(( ( ( - 1.0 ) ) ) / taufgaba)))*(- ( ( ( 1.0 ) ) / taufgaba ) / ( ( ( ( - 1.0 ) ) ) / taufgaba ) - fgaba) ;
   }
  return 0;
}
 
static int _ode_count(int _type){ return 4;}
 
static void _ode_spec(NrnThread* _nt, Memb_list* _ml, int _type) {
   double* _p; Datum* _ppvar; Datum* _thread;
   Node* _nd; double _v; int _iml, _cntml;
  _cntml = _ml->_nodecount;
  _thread = _ml->_thread;
  for (_iml = 0; _iml < _cntml; ++_iml) {
    _p = _ml->_data[_iml]; _ppvar = _ml->_pdata[_iml];
    _nd = _ml->_nodelist[_iml];
    v = NODEV(_nd);
     _ode_spec1 (_p, _ppvar, _thread, _nt);
 }}
 
static void _ode_map(int _ieq, double** _pv, double** _pvdot, double* _pp, Datum* _ppd, double* _atol, int _type) { 
	double* _p; Datum* _ppvar;
 	int _i; _p = _pp; _ppvar = _ppd;
	_cvode_ieq = _ieq;
	for (_i=0; _i < 4; ++_i) {
		_pv[_i] = _pp + _slist1[_i];  _pvdot[_i] = _pp + _dlist1[_i];
		_cvode_abstol(_atollist, _atol, _i);
	}
 }
 
static void _ode_matsol_instance1(_threadargsproto_) {
 _ode_matsol1 (_p, _ppvar, _thread, _nt);
 }
 
static void _ode_matsol(NrnThread* _nt, Memb_list* _ml, int _type) {
   double* _p; Datum* _ppvar; Datum* _thread;
   Node* _nd; double _v; int _iml, _cntml;
  _cntml = _ml->_nodecount;
  _thread = _ml->_thread;
  for (_iml = 0; _iml < _cntml; ++_iml) {
    _p = _ml->_data[_iml]; _ppvar = _ml->_pdata[_iml];
    _nd = _ml->_nodelist[_iml];
    v = NODEV(_nd);
 _ode_matsol_instance1(_threadargs_);
 }}

static void initmodel(double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt) {
  int _i; double _save;{
  D = D0;
  R = R0;
  dgaba = dgaba0;
  fgaba = fgaba0;
 {
   double _ltp ;
 dgaba = 1.0 ;
   fgaba = 1.0 ;
   R = 0.0 ;
   D = 0.0 ;
   ggaba = 0.0 ;
   _ltp = ( risetime * decaytime ) / ( decaytime - risetime ) * log ( decaytime / risetime ) ;
   factor = - exp ( - _ltp / risetime ) + exp ( - _ltp / decaytime ) ;
   factor = 1.0 / factor ;
   }
 
}
}

static void nrn_init(NrnThread* _nt, Memb_list* _ml, int _type){
double* _p; Datum* _ppvar; Datum* _thread;
Node *_nd; double _v; int* _ni; int _iml, _cntml;
#if CACHEVEC
    _ni = _ml->_nodeindices;
#endif
_cntml = _ml->_nodecount;
_thread = _ml->_thread;
for (_iml = 0; _iml < _cntml; ++_iml) {
 _p = _ml->_data[_iml]; _ppvar = _ml->_pdata[_iml];
 _tsav = -1e20;
#if CACHEVEC
  if (use_cachevec) {
    _v = VEC_V(_ni[_iml]);
  }else
#endif
  {
    _nd = _ml->_nodelist[_iml];
    _v = NODEV(_nd);
  }
 v = _v;
 initmodel(_p, _ppvar, _thread, _nt);
}
}

static double _nrn_current(double* _p, Datum* _ppvar, Datum* _thread, NrnThread* _nt, double _v){double _current=0.;v=_v;{ {
   ggaba = D - R ;
   i = ( 1e-3 ) * ggaba * ( v - e ) ;
   }
 _current += i;

} return _current;
}

static void nrn_cur(NrnThread* _nt, Memb_list* _ml, int _type) {
double* _p; Datum* _ppvar; Datum* _thread;
Node *_nd; int* _ni; double _rhs, _v; int _iml, _cntml;
#if CACHEVEC
    _ni = _ml->_nodeindices;
#endif
_cntml = _ml->_nodecount;
_thread = _ml->_thread;
for (_iml = 0; _iml < _cntml; ++_iml) {
 _p = _ml->_data[_iml]; _ppvar = _ml->_pdata[_iml];
#if CACHEVEC
  if (use_cachevec) {
    _v = VEC_V(_ni[_iml]);
  }else
#endif
  {
    _nd = _ml->_nodelist[_iml];
    _v = NODEV(_nd);
  }
 _g = _nrn_current(_p, _ppvar, _thread, _nt, _v + .001);
 	{ _rhs = _nrn_current(_p, _ppvar, _thread, _nt, _v);
 	}
 _g = (_g - _rhs)/.001;
 _g *=  1.e2/(_nd_area);
 _rhs *= 1.e2/(_nd_area);
#if CACHEVEC
  if (use_cachevec) {
	VEC_RHS(_ni[_iml]) -= _rhs;
  }else
#endif
  {
	NODERHS(_nd) -= _rhs;
  }
 
}
 
}

static void nrn_jacob(NrnThread* _nt, Memb_list* _ml, int _type) {
double* _p; Datum* _ppvar; Datum* _thread;
Node *_nd; int* _ni; int _iml, _cntml;
#if CACHEVEC
    _ni = _ml->_nodeindices;
#endif
_cntml = _ml->_nodecount;
_thread = _ml->_thread;
for (_iml = 0; _iml < _cntml; ++_iml) {
 _p = _ml->_data[_iml];
#if CACHEVEC
  if (use_cachevec) {
	VEC_D(_ni[_iml]) += _g;
  }else
#endif
  {
     _nd = _ml->_nodelist[_iml];
	NODED(_nd) += _g;
  }
 
}
 
}

static void nrn_state(NrnThread* _nt, Memb_list* _ml, int _type) {
double* _p; Datum* _ppvar; Datum* _thread;
Node *_nd; double _v = 0.0; int* _ni; int _iml, _cntml;
#if CACHEVEC
    _ni = _ml->_nodeindices;
#endif
_cntml = _ml->_nodecount;
_thread = _ml->_thread;
for (_iml = 0; _iml < _cntml; ++_iml) {
 _p = _ml->_data[_iml]; _ppvar = _ml->_pdata[_iml];
 _nd = _ml->_nodelist[_iml];
#if CACHEVEC
  if (use_cachevec) {
    _v = VEC_V(_ni[_iml]);
  }else
#endif
  {
    _nd = _ml->_nodelist[_iml];
    _v = NODEV(_nd);
  }
 v=_v;
{
 {   state(_p, _ppvar, _thread, _nt);
  }}}

}

static void terminal(){}

static void _initlists(){
 double _x; double* _p = &_x;
 int _i; static int _first = 1;
  if (!_first) return;
 _slist1[0] = R_columnindex;  _dlist1[0] = DR_columnindex;
 _slist1[1] = D_columnindex;  _dlist1[1] = DD_columnindex;
 _slist1[2] = dgaba_columnindex;  _dlist1[2] = Ddgaba_columnindex;
 _slist1[3] = fgaba_columnindex;  _dlist1[3] = Dfgaba_columnindex;
_first = 0;
}

#if NMODL_TEXT
static void register_nmodl_text_and_filename(int mech_type) {
    const char* nmodl_filename = "/gpfs/soma_fs/scratch/saka/project_src/in_silico_framework/mechanisms/channels_py3_wip/netgaba.mod";
    const char* nmodl_file_text = 
  "COMMENT\n"
  "//****************************//\n"
  "// Created by Alon Polsky 	//\n"
  "//    apmega@yahoo.com		//\n"
  "//		2010			//\n"
  "//****************************//\n"
  "based on Sun et al 2006\n"
  "Modified 2015 by Robert Egger\n"
  "to include facilitation variable\n"
  "as modeled by Varela et al. 1997\n"
  "ENDCOMMENT\n"
  "TITLE GABAA synapse activated by the network\n"
  "NEURON {\n"
  "	POINT_PROCESS gaba_syn\n"
  "	NONSPECIFIC_CURRENT i\n"
  "	RANGE i,ggaba\n"
  "	RANGE decaygaba,dgaba,taudgaba\n"
  "	RANGE facilgaba,fgaba,taufgaba\n"
  "	:RANGE R,D\n"
  "	RANGE risetime,decaytime,e \n"
  "}\n"
  "PARAMETER {\n"
  "	e= -60.0	(mV)\n"
  "	risetime=1	(ms)	:2\n"
  "	decaytime=20(ms)	:40\n"
  "\n"
  "	v		(mV)\n"
  "	taudgaba=200	(ms)\n"
  "	decaygaba=0.8\n"
  "	taufgaba=200    (ms)\n"
  "	facilgaba=0.0\n"
  "}\n"
  "ASSIGNED {\n"
  "	i		(nA)  \n"
  "	ggaba\n"
  "    factor     : conductance normalization factor\n"
  "}\n"
  "\n"
  "STATE {\n"
  "	dgaba\n"
  "	fgaba\n"
  "	R\n"
  "	D\n"
  "}\n"
  "\n"
  "INITIAL {\n"
  "	LOCAL tp\n"
  "    dgaba=1 \n"
  "    fgaba=1\n"
  "	R=0\n"
  "	D=0\n"
  "	ggaba=0\n"
  "	\n"
  "    tp = (risetime*decaytime)/(decaytime - risetime) * log(decaytime/risetime)\n"
  "    factor = -exp(-tp/risetime) + exp(-tp/decaytime)\n"
  "    factor = 1/factor\n"
  "}\n"
  "BREAKPOINT {\n"
  "	SOLVE state METHOD cnexp\n"
  "	ggaba=D-R\n"
  "	i=(1e-3)*ggaba*(v-e)\n"
  "}\n"
  "NET_RECEIVE(weight) {\n"
  "    R = R + factor*weight*dgaba*fgaba\n"
  "    D = D + factor*weight*dgaba*fgaba\n"
  "    dgaba = dgaba* decaygaba\n"
  "    fgaba = fgaba + facilgaba\n"
  "}\n"
  "DERIVATIVE state {\n"
  "	R'=-R/risetime\n"
  "	D'=-D/decaytime\n"
  "	dgaba'=(1-dgaba)/taudgaba\n"
  "	fgaba'=(1-fgaba)/taufgaba\n"
  "\n"
  "}\n"
  ;
    hoc_reg_nmodl_filename(mech_type, nmodl_filename);
    hoc_reg_nmodl_text(mech_type, nmodl_file_text);
}
#endif
