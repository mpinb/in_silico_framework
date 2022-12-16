/* Created by Language version: 6.2.0 */
/* VECTORIZED */
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#undef PI
 
#include "coreneuron/utils/randoms/nrnran123.h"
#include "coreneuron/nrnoc/md1redef.h"
#include "coreneuron/nrnconf.h"
#include "coreneuron/sim/multicore.hpp"
#include "coreneuron/nrniv/nrniv_decl.h"
#include "coreneuron/utils/ivocvect.hpp"
#include "coreneuron/utils/nrnoc_aux.hpp"
#include "coreneuron/gpu/nrn_acc_manager.hpp"
#include "coreneuron/sim/scopmath/newton_struct.h"
#include "coreneuron/sim/scopmath/newton_thread.hpp"
#include "coreneuron/sim/scopmath/sparse_thread.hpp"
#include "coreneuron/sim/scopmath/ssimplic_thread.hpp"
#include "coreneuron/nrnoc/md2redef.h"
#include "coreneuron/mechanism/register_mech.hpp"
#if !NRNGPU
#if !defined(DISABLE_HOC_EXP)
#undef exp
#define exp hoc_Exp
#endif
#endif
 namespace coreneuron {
 
#define _thread_present_ /**/ 
 
#if defined(_OPENACC) && !defined(DISABLE_OPENACC)
#include <openacc.h>
#define _PRAGMA_FOR_INIT_ACC_LOOP_ _Pragma("acc parallel loop present(_ni[0:_cntml_actual], _nt_data[0:_nt->_ndata], _p[0:_cntml_padded*_psize], _ppvar[0:_cntml_padded*_ppsize], _vec_v[0:_nt->end], nrn_ion_global_map[0:nrn_ion_global_map_size][0:ion_global_map_member_size], _nt[0:1] _thread_present_) if(_nt->compute_gpu)")
#define _PRAGMA_FOR_STATE_ACC_LOOP_ _Pragma("acc parallel loop present(_ni[0:_cntml_actual], _nt_data[0:_nt->_ndata], _p[0:_cntml_padded*_psize], _ppvar[0:_cntml_padded*_ppsize], _vec_v[0:_nt->end], _nt[0:1], _ml[0:1] _thread_present_) if(_nt->compute_gpu) async(stream_id)")
#define _PRAGMA_FOR_CUR_ACC_LOOP_ _Pragma("acc parallel loop present(_ni[0:_cntml_actual], _nt_data[0:_nt->_ndata], _p[0:_cntml_padded*_psize], _ppvar[0:_cntml_padded*_ppsize], _vec_v[0:_nt->end], _vec_d[0:_nt->end], _vec_rhs[0:_nt->end], _nt[0:1] _thread_present_) if(_nt->compute_gpu) async(stream_id)")
#define _PRAGMA_FOR_CUR_SYN_ACC_LOOP_ _Pragma("acc parallel loop present(_ni[0:_cntml_actual], _nt_data[0:_nt->_ndata], _p[0:_cntml_padded*_psize], _ppvar[0:_cntml_padded*_ppsize], _vec_v[0:_nt->end], _vec_shadow_rhs[0:_nt->shadow_rhs_cnt], _vec_shadow_d[0:_nt->shadow_rhs_cnt], _vec_d[0:_nt->end], _vec_rhs[0:_nt->end], _nt[0:1]) if(_nt->compute_gpu) async(stream_id)")
#define _PRAGMA_FOR_NETRECV_ACC_LOOP_ _Pragma("acc parallel loop present(_pnt[0:_pnt_length], _nrb[0:1], _nt[0:1], nrn_threads[0:nrn_nthread]) if(_nt->compute_gpu) async(stream_id)")
#else
#define _PRAGMA_FOR_INIT_ACC_LOOP_ _Pragma("")
#define _PRAGMA_FOR_STATE_ACC_LOOP_ _Pragma("")
#define _PRAGMA_FOR_CUR_ACC_LOOP_ _Pragma("")
#define _PRAGMA_FOR_CUR_SYN_ACC_LOOP_ _Pragma("")
#define _PRAGMA_FOR_NETRECV_ACC_LOOP_ _Pragma("")
#endif
 
#if defined(__ICC) || defined(__INTEL_COMPILER)
#define _PRAGMA_FOR_VECTOR_LOOP_ _Pragma("ivdep")
#elif defined(__IBMC__) || defined(__IBMCPP__)
#define _PRAGMA_FOR_VECTOR_LOOP_ _Pragma("ibm independent_loop")
#elif defined(__PGI)
#define _PRAGMA_FOR_VECTOR_LOOP_ _Pragma("vector")
#elif defined(_CRAYC)
#define _PRAGMA_FOR_VECTOR_LOOP_ _Pragma("_CRI ivdep")
#elif defined(__clang__)
#define _PRAGMA_FOR_VECTOR_LOOP_ _Pragma("clang loop vectorize(enable)")
#elif defined(__GNUC__) || defined(__GNUG__)
#define _PRAGMA_FOR_VECTOR_LOOP_ _Pragma("GCC ivdep")
#else
#define _PRAGMA_FOR_VECTOR_LOOP_
#endif // _PRAGMA_FOR_VECTOR_LOOP_
 
#if !defined(LAYOUT)
/* 1 means AoS, >1 means AoSoA, <= 0 means SOA */
#define LAYOUT 1
#endif
#if LAYOUT >= 1
#define _STRIDE LAYOUT
#else
#define _STRIDE _cntml_padded + _iml
#endif
 

#if !defined(NET_RECEIVE_BUFFERING)
#define NET_RECEIVE_BUFFERING 1
#endif
 
#define nrn_init _nrn_init__glutamate_syn
#define nrn_cur _nrn_cur__glutamate_syn
#define _nrn_current _nrn_current__glutamate_syn
#define nrn_jacob _nrn_jacob__glutamate_syn
#define nrn_state _nrn_state__glutamate_syn
#define initmodel initmodel__glutamate_syn
#define _net_receive _net_receive__glutamate_syn
#define _net_init _net_init__glutamate_syn
#define nrn_state_launcher nrn_state_glutamate_syn_launcher
#define nrn_cur_launcher nrn_cur_glutamate_syn_launcher
#define nrn_jacob_launcher nrn_jacob_glutamate_syn_launcher 
#if NET_RECEIVE_BUFFERING
#define _net_buf_receive _net_buf_receive_glutamate_syn
void _net_buf_receive(NrnThread*);
#endif
 
#define state state_glutamate_syn 
 
#undef _threadargscomma_
#undef _threadargsprotocomma_
#undef _threadargs_
#undef _threadargsproto_
 
#define _threadargscomma_ _iml, _cntml_padded, _p, _ppvar, _thread, _nt, _ml, v,
#define _threadargsprotocomma_ int _iml, int _cntml_padded, double* _p, Datum* _ppvar, ThreadDatum* _thread, NrnThread* _nt, Memb_list* _ml, double v,
#define _threadargs_ _iml, _cntml_padded, _p, _ppvar, _thread, _nt, _ml, v
#define _threadargsproto_ int _iml, int _cntml_padded, double* _p, Datum* _ppvar, ThreadDatum* _thread, NrnThread* _nt, Memb_list* _ml, double v
 	/*SUPPRESS 761*/
	/*SUPPRESS 762*/
	/*SUPPRESS 763*/
	/*SUPPRESS 765*/
	 /* Thread safe. No static _p or _ppvar. */
 
#define t _nt->_t
#define dt _nt->_dt
#define gnmdamax _p[0*_STRIDE]
#define gampamax _p[1*_STRIDE]
#define e _p[2*_STRIDE]
#define tau1 _p[3*_STRIDE]
#define tau2 _p[4*_STRIDE]
#define tau3 _p[5*_STRIDE]
#define tau4 _p[6*_STRIDE]
#define decayampa _p[7*_STRIDE]
#define decaynmda _p[8*_STRIDE]
#define taudampa _p[9*_STRIDE]
#define taudnmda _p[10*_STRIDE]
#define taufampa _p[11*_STRIDE]
#define facilampa _p[12*_STRIDE]
#define taufnmda _p[13*_STRIDE]
#define facilnmda _p[14*_STRIDE]
#define inmda _p[15*_STRIDE]
#define iampa _p[16*_STRIDE]
#define gnmda _p[17*_STRIDE]
#define gampa _p[18*_STRIDE]
#define A _p[19*_STRIDE]
#define B _p[20*_STRIDE]
#define C _p[21*_STRIDE]
#define D _p[22*_STRIDE]
#define dampa _p[23*_STRIDE]
#define dnmda _p[24*_STRIDE]
#define fampa _p[25*_STRIDE]
#define fnmda _p[26*_STRIDE]
#define factor1 _p[27*_STRIDE]
#define factor2 _p[28*_STRIDE]
#define DA _p[29*_STRIDE]
#define DB _p[30*_STRIDE]
#define DC _p[31*_STRIDE]
#define DD _p[32*_STRIDE]
#define Ddampa _p[33*_STRIDE]
#define Ddnmda _p[34*_STRIDE]
#define Dfampa _p[35*_STRIDE]
#define Dfnmda _p[36*_STRIDE]
#define _v_unused _p[37*_STRIDE]
#define _g_unused _p[38*_STRIDE]
#define _tsav _p[39*_STRIDE]
 
#ifndef NRN_PRCELLSTATE
#define NRN_PRCELLSTATE 0
#endif
#if NRN_PRCELLSTATE
#define _PRCELLSTATE_V _v_unused = _v;
#define _PRCELLSTATE_G _g_unused = _g;
#else
#define _PRCELLSTATE_V /**/
#define _PRCELLSTATE_G /**/
#endif
#define _nd_area  _nt_data[_ppvar[0*_STRIDE]]
 
#if MAC
#if !defined(v)
#define v _mlhv
#endif
#if !defined(h)
#define h _mlhh
#endif
#endif
 static int hoc_nrnpointerindex =  -1;
 static ThreadDatum* _extcall_thread;
 /* external NEURON variables */
 extern double celsius;
 #define nrn_ghk(v, ci, co, z) nrn_ghk(v, ci, co, z, celsius)
 #if 0 /*BBCORE*/
 /* declaration of user functions */
 
#endif /*BBCORE*/
 static int _mechtype;
 static int _pointtype;
 
#if 0 /*BBCORE*/
 static void* _hoc_create_pnt(_ho) Object* _ho; { void* create_point_process();
 return create_point_process(_pointtype, _ho);
}
 static void _hoc_destroy_pnt();
 static double _hoc_loc_pnt(_vptr) void* _vptr; {double loc_point_process();
 return loc_point_process(_pointtype, _vptr);
}
 static double _hoc_has_loc(_vptr) void* _vptr; {double has_loc_point();
 return has_loc_point(_vptr);
}
 static double _hoc_get_loc_pnt(_vptr)void* _vptr; {
 double get_loc_point_process(); return (get_loc_point_process(_vptr));
}
 
#endif /*BBCORE*/
 
#if 0 /*BBCORE*/
 /* connect user functions to hoc names */
 static VoidFunc hoc_intfunc[] = {
 0,0
};
 static Member_func _member_func[] = {
 "loc", _hoc_loc_pnt,
 "has_loc", _hoc_has_loc,
 "get_loc", _hoc_get_loc_pnt,
 0, 0
};
 
#endif /*BBCORE*/
 /* declare global and static user variables */
 static double gama_glutamate_syn = 0.08;
 static double n_glutamate_syn = 0.25;
 static double tau_ampa_glutamate_syn = 2;
 
#if 0 /*BBCORE*/
 /* some parameters have upper and lower limits */
 static HocParmLimits _hoc_parm_limits[] = {
 0,0,0
};
 static HocParmUnits _hoc_parm_units[] = {
 "tau_ampa_glutamate_syn", "ms",
 "n_glutamate_syn", "/mM",
 "gama_glutamate_syn", "/mV",
 "gnmdamax", "nS",
 "gampamax", "nS",
 "e", "mV",
 "tau1", "ms",
 "tau2", "ms",
 "tau3", "ms",
 "tau4", "ms",
 "taudampa", "ms",
 "taudnmda", "ms",
 "taufampa", "ms",
 "taufnmda", "ms",
 "A", "nS",
 "B", "nS",
 "C", "nS",
 "D", "nS",
 "inmda", "nA",
 "iampa", "nA",
 "gnmda", "nS",
 "gampa", "nS",
 0,0
};
 
#endif /*BBCORE*/
 static double A0 = 0;
 static double B0 = 0;
 static double C0 = 0;
 static double D0 = 0;
 static double delta_t = 0.01;
 static double dnmda0 = 0;
 static double dampa0 = 0;
 static double fnmda0 = 0;
 static double fampa0 = 0;
 /* connect global user variables to hoc */
 static DoubScal hoc_scdoub[] = {
 "tau_ampa_glutamate_syn", &tau_ampa_glutamate_syn,
 "n_glutamate_syn", &n_glutamate_syn,
 "gama_glutamate_syn", &gama_glutamate_syn,
 0,0
};
 static DoubVec hoc_vdoub[] = {
 0,0,0
};
 static double _sav_indep;
 static void _create_global_variables(NrnThread*, Memb_list*, int);
 static void _destroy_global_variables(NrnThread*, Memb_list*, int);
 static void nrn_alloc(double*, Datum*, int);
void nrn_init(NrnThread*, Memb_list*, int);
void nrn_state(NrnThread*, Memb_list*, int);
 void nrn_cur(NrnThread*, Memb_list*, int);
 
#if 0 /*BBCORE*/
 static void _hoc_destroy_pnt(_vptr) void* _vptr; {
   destroy_point_process(_vptr);
}
 
#endif /*BBCORE*/
 /* connect range variables in _p that hoc is supposed to know about */
 static const char *_mechanism[] = {
 "6.2.0",
"glutamate_syn",
 "gnmdamax",
 "gampamax",
 "e",
 "tau1",
 "tau2",
 "tau3",
 "tau4",
 "decayampa",
 "decaynmda",
 "taudampa",
 "taudnmda",
 "taufampa",
 "facilampa",
 "taufnmda",
 "facilnmda",
 0,
 "inmda",
 "iampa",
 "gnmda",
 "gampa",
 0,
 "A",
 "B",
 "C",
 "D",
 "dampa",
 "dnmda",
 "fampa",
 "fnmda",
 0,
 0};
 
static void nrn_alloc(double* _p, Datum* _ppvar, int _type) {
 
#if 0 /*BBCORE*/
 	/*initialize range parameters*/
 	gnmdamax = 1;
 	gampamax = 1;
 	e = 0;
 	tau1 = 50;
 	tau2 = 2;
 	tau3 = 2;
 	tau4 = 0.1;
 	decayampa = 0.5;
 	decaynmda = 0.5;
 	taudampa = 200;
 	taudnmda = 200;
 	taufampa = 200;
 	facilampa = 0;
 	taufnmda = 200;
 	facilnmda = 0;
 
#endif /* BBCORE */
 
}
 static void _initlists(Memb_list *_ml);
 void _net_receive(Point_process*, int, double);
 void _net_init(Point_process*, int, double);
 
#define _psize 40
#define _ppsize 2
 void _netglutamate_reg() {
	int _vectorized = 1;
  _mechtype = nrn_get_mechtype(_mechanism[1]);
 if (_mechtype == -1) return;
 _nrn_layout_reg(_mechtype, LAYOUT);
 
#if 0 /*BBCORE*/
 
#endif /*BBCORE*/
 	_pointtype = point_register_mech(_mechanism,
	 nrn_alloc,nrn_cur, NULL, nrn_state, nrn_init, _create_global_variables, _destroy_global_variables,
	 hoc_nrnpointerindex,
	 NULL/*_hoc_create_pnt*/, NULL/*_hoc_destroy_pnt*/, /*_member_func,*/
	 1);
  hoc_register_prop_size(_mechtype, _psize, _ppsize);
  hoc_register_dparam_semantics(_mechtype, 0, "area");
  hoc_register_dparam_semantics(_mechtype, 1, "pntproc");
 
#if NET_RECEIVE_BUFFERING
  hoc_register_net_receive_buffering(_net_buf_receive, _mechtype);
#endif
 set_pnt_receive(_mechtype, _net_receive, _net_init, 2);
 	hoc_register_var(hoc_scdoub, hoc_vdoub, NULL);
 }
 struct _global_variables_t : public MemoryManaged {
   int _slist1[8];
   int _dlist1[8];
   double celsius;
   double gama;
   double n;
   double tau_ampa;
   double A0;
   double B0;
   double C0;
   double D0;
   double delta_t;
   double dnmda0;
   double dampa0;
   double fnmda0;
   double fampa0;
 };

 
static void _create_global_variables(NrnThread *_nt, Memb_list *_ml, int _type) {
   assert(!_ml->global_variables);
   _ml->global_variables = new _global_variables_t{};
   _ml->global_variables_size = sizeof(_global_variables_t);
 }
 
static void _destroy_global_variables(NrnThread *_nt, Memb_list *_ml, int _type) {
   delete static_cast<_global_variables_t*>(_ml->global_variables);
   _ml->global_variables = nullptr;
   _ml->global_variables_size = 0;
 }
 
static void _update_global_variables(NrnThread *_nt, Memb_list *_ml) {
   if(!_nt || !_ml) {
     return;
   }
   auto* const _global_variables = static_cast<_global_variables_t*>(_ml->global_variables);
   _global_variables->celsius = celsius;
   _global_variables->gama = gama_glutamate_syn;
   _global_variables->n = n_glutamate_syn;
   _global_variables->tau_ampa = tau_ampa_glutamate_syn;
   _global_variables->A0 = A0;
   _global_variables->B0 = B0;
   _global_variables->C0 = C0;
   _global_variables->D0 = D0;
   _global_variables->delta_t = delta_t;
   _global_variables->dnmda0 = dnmda0;
   _global_variables->dampa0 = dampa0;
   _global_variables->fnmda0 = fnmda0;
   _global_variables->fampa0 = fampa0;
 #ifdef CORENEURON_ENABLE_GPU
   if (_nt->compute_gpu) {
       cnrn_target_update_on_device(_global_variables);
   }
 #endif
 }

 #define _slist1 static_cast<_global_variables_t*>(_ml->global_variables)->_slist1
 #define _dlist1 static_cast<_global_variables_t*>(_ml->global_variables)->_dlist1
 #define celsius static_cast<_global_variables_t*>(_ml->global_variables)->celsius
 #define gama static_cast<_global_variables_t*>(_ml->global_variables)->gama
 #define n static_cast<_global_variables_t*>(_ml->global_variables)->n
 #define tau_ampa static_cast<_global_variables_t*>(_ml->global_variables)->tau_ampa
 #define A0 static_cast<_global_variables_t*>(_ml->global_variables)->A0
 #define B0 static_cast<_global_variables_t*>(_ml->global_variables)->B0
 #define C0 static_cast<_global_variables_t*>(_ml->global_variables)->C0
 #define D0 static_cast<_global_variables_t*>(_ml->global_variables)->D0
 #define delta_t static_cast<_global_variables_t*>(_ml->global_variables)->delta_t
 #define dnmda0 static_cast<_global_variables_t*>(_ml->global_variables)->dnmda0
 #define dampa0 static_cast<_global_variables_t*>(_ml->global_variables)->dampa0
 #define fnmda0 static_cast<_global_variables_t*>(_ml->global_variables)->fnmda0
 #define fampa0 static_cast<_global_variables_t*>(_ml->global_variables)->fampa0
 
static const char *modelname = "NMDA synapse with depression";

static int error;
static int _ninits = 0;
static int _match_recurse=1;
static void _modl_cleanup(){ _match_recurse=1;}
 
static int _ode_spec1(_threadargsproto_);
/*static int _ode_matsol1(_threadargsproto_);*/
 static inline int state(_threadargsproto_);
 
#if NET_RECEIVE_BUFFERING 
#undef t
#define t _nrb_t
static inline void _net_receive_kernel(NrnThread*, double, Point_process*, int _weight_index, double _flag);
void _net_buf_receive(NrnThread* _nt) {
  if (!_nt->_ml_list) { return; }
  Memb_list* _ml = _nt->_ml_list[_mechtype];
  if (!_ml) { return; }
  NetReceiveBuffer_t* _nrb = _ml->_net_receive_buffer; 
  int _di;
  int stream_id = _nt->stream_id;
  Point_process* _pnt = _nt->pntprocs;
  int _pnt_length = _nt->n_pntproc - _nrb->_pnt_offset;
  int _displ_cnt = _nrb->_displ_cnt;
  _PRAGMA_FOR_NETRECV_ACC_LOOP_ 
  for (_di = 0; _di < _displ_cnt; ++_di) {
    int _inrb;
    int _di0 = _nrb->_displ[_di];
    int _di1 = _nrb->_displ[_di + 1];
    for (_inrb = _di0; _inrb < _di1; ++_inrb) {
      int _i = _nrb->_nrb_index[_inrb];
      int _j = _nrb->_pnt_index[_i];
      int _k = _nrb->_weight_index[_i];
      double _nrt = _nrb->_nrb_t[_i];
      double _nrflag = _nrb->_nrb_flag[_i];
      _net_receive_kernel(nrn_threads, _nrt, _pnt + _j, _k, _nrflag);
    }
  }
  #pragma acc wait(stream_id)
  _nrb->_displ_cnt = 0;
  _nrb->_cnt = 0;
  /*printf("_net_buf_receive__glutamate_syn  %d\n", _nt->_id);*/
 
}
 
void _net_receive (Point_process* _pnt, int _weight_index, double _lflag) {
  NrnThread* _nt = nrn_threads + _pnt->_tid;
  NetReceiveBuffer_t* _nrb = _nt->_ml_list[_mechtype]->_net_receive_buffer;
  if (_nrb->_cnt >= _nrb->_size){
    realloc_net_receive_buffer(_nt, _nt->_ml_list[_mechtype]);
  }
  _nrb->_pnt_index[_nrb->_cnt] = _pnt - _nt->pntprocs;
  _nrb->_weight_index[_nrb->_cnt] = _weight_index;
  _nrb->_nrb_t[_nrb->_cnt] = _nt->_t;
  _nrb->_nrb_flag[_nrb->_cnt] = _lflag;
  ++_nrb->_cnt;
}
 
static void _net_receive_kernel(NrnThread* nrn_threads, double _nrb_t, Point_process* _pnt, int _weight_index, double _lflag)
#else
 
void _net_receive (Point_process* _pnt, int _weight_index, double _lflag) 
#endif
 
{  double* _p; Datum* _ppvar; ThreadDatum* _thread; double v = 0;
   Memb_list* _ml; int _cntml_padded, _cntml_actual; int _iml; double* _args;
 
   NrnThread* _nt;
   int _tid = _pnt->_tid; 
   _nt = nrn_threads + _tid;
   _thread = (ThreadDatum*)0; 
   double *_weights = _nt->_weights;
   _args = _weights ? _weights + _weight_index : nullptr;
   _ml = _nt->_ml_list[_pnt->_type];
   _cntml_actual = _ml->_nodecount;
   _cntml_padded = _ml->_nodecount_padded;
   _iml = _pnt->_i_instance;
#if LAYOUT == 1 /*AoS*/
   _p = _ml->_data + _iml*_psize; _ppvar = _ml->_pdata + _iml*_ppsize;
#endif
#if LAYOUT == 0 /*SoA*/
   _p = _ml->_data; _ppvar = _ml->_pdata;
#endif
#if LAYOUT > 1 /*AoSoA*/
#error AoSoA not implemented.
#endif
  #if !defined(_OPENACC) 
 assert(_tsav <= t); 
 #endif 
 _tsav = t; {
   gampamax = _args[0] ;
   gnmdamax = _args[1] ;
   A = A + factor1 * gnmdamax * dnmda * fnmda ;
   B = B + factor1 * gnmdamax * dnmda * fnmda ;
   C = C + factor2 * gampamax * dampa * fampa ;
   D = D + factor2 * gampamax * dampa * fampa ;
   dampa = dampa * decayampa ;
   dnmda = dnmda * decaynmda ;
   fampa = fampa + facilampa ;
   fnmda = fnmda + facilnmda ;
   } 
#if NET_RECEIVE_BUFFERING
#undef t
#define t _nt->_t
#endif
 }
 
void _net_init(Point_process* _pnt, int _weight_index, double _lflag) {
   
   double* _p; Datum* _ppvar; ThreadDatum* _thread; double v = 0;
   Memb_list* _ml; int _cntml_padded, _cntml_actual; int _iml; double* _args;
 
   NrnThread* _nt;
   int _tid = _pnt->_tid; 
   _nt = nrn_threads + _tid;
   _thread = (ThreadDatum*)0; 
   double *_weights = _nt->_weights;
   _args = _weights ? _weights + _weight_index : nullptr;
   _ml = _nt->_ml_list[_pnt->_type];
   _cntml_actual = _ml->_nodecount;
   _cntml_padded = _ml->_nodecount_padded;
   _iml = _pnt->_i_instance;
#if LAYOUT == 1 /*AoS*/
   _p = _ml->_data + _iml*_psize; _ppvar = _ml->_pdata + _iml*_ppsize;
#endif
#if LAYOUT == 0 /*SoA*/
   _p = _ml->_data; _ppvar = _ml->_pdata;
#endif
#if LAYOUT > 1 /*AoSoA*/
#error AoSoA not implemented.
#endif
   v = VEC_V(_ml->_nodeindices[_iml]);
  gampamax = _args[0] ;
   gnmdamax = _args[1] ;
   }
 
/*CVODE*/
 static int _ode_spec1 (_threadargsproto_) {int _reset = 0; {
   DA = - A / tau1 ;
   DB = - B / tau2 ;
   DC = - C / tau3 ;
   DD = - D / tau4 ;
   Ddampa = ( 1.0 - dampa ) / taudampa ;
   Ddnmda = ( 1.0 - dnmda ) / taudnmda ;
   Dfampa = ( 1.0 - fampa ) / taufampa ;
   Dfnmda = ( 1.0 - fnmda ) / taufnmda ;
   }
 return _reset;
}
 static int _ode_matsol1 (_threadargsproto_) {
 DA = DA  / (1. - dt*( ( - 1.0 ) / tau1 )) ;
 DB = DB  / (1. - dt*( ( - 1.0 ) / tau2 )) ;
 DC = DC  / (1. - dt*( ( - 1.0 ) / tau3 )) ;
 DD = DD  / (1. - dt*( ( - 1.0 ) / tau4 )) ;
 Ddampa = Ddampa  / (1. - dt*( ( ( ( - 1.0 ) ) ) / taudampa )) ;
 Ddnmda = Ddnmda  / (1. - dt*( ( ( ( - 1.0 ) ) ) / taudnmda )) ;
 Dfampa = Dfampa  / (1. - dt*( ( ( ( - 1.0 ) ) ) / taufampa )) ;
 Dfnmda = Dfnmda  / (1. - dt*( ( ( ( - 1.0 ) ) ) / taufnmda )) ;
 return 0;
}
 /*END CVODE*/
 static int state (_threadargsproto_) { {
    A = A + (1. - exp(dt*(( - 1.0 ) / tau1)))*(- ( 0.0 ) / ( ( - 1.0 ) / tau1 ) - A) ;
    B = B + (1. - exp(dt*(( - 1.0 ) / tau2)))*(- ( 0.0 ) / ( ( - 1.0 ) / tau2 ) - B) ;
    C = C + (1. - exp(dt*(( - 1.0 ) / tau3)))*(- ( 0.0 ) / ( ( - 1.0 ) / tau3 ) - C) ;
    D = D + (1. - exp(dt*(( - 1.0 ) / tau4)))*(- ( 0.0 ) / ( ( - 1.0 ) / tau4 ) - D) ;
    dampa = dampa + (1. - exp(dt*(( ( ( - 1.0 ) ) ) / taudampa)))*(- ( ( ( 1.0 ) ) / taudampa ) / ( ( ( ( - 1.0) ) ) / taudampa ) - dampa) ;
    dnmda = dnmda + (1. - exp(dt*(( ( ( - 1.0 ) ) ) / taudnmda)))*(- ( ( ( 1.0 ) ) / taudnmda ) / ( ( ( ( - 1.0) ) ) / taudnmda ) - dnmda) ;
    fampa = fampa + (1. - exp(dt*(( ( ( - 1.0 ) ) ) / taufampa)))*(- ( ( ( 1.0 ) ) / taufampa ) / ( ( ( ( - 1.0) ) ) / taufampa ) - fampa) ;
    fnmda = fnmda + (1. - exp(dt*(( ( ( - 1.0 ) ) ) / taufnmda)))*(- ( ( ( 1.0 ) ) / taufnmda ) / ( ( ( ( - 1.0) ) ) / taufnmda ) - fnmda) ;
   }
  return 0;
}

static inline void initmodel(_threadargsproto_) {
  int _i; double _save;{
  A = A0;
  B = B0;
  C = C0;
  D = D0;
  dnmda = dnmda0;
  dampa = dampa0;
  fnmda = fnmda0;
  fampa = fampa0;
 {
   double _ltp1 , _ltp2 ;
 gnmda = 0.0 ;
   gampa = 0.0 ;
   A = 0.0 ;
   B = 0.0 ;
   C = 0.0 ;
   D = 0.0 ;
   dampa = 1.0 ;
   dnmda = 1.0 ;
   fampa = 1.0 ;
   fnmda = 1.0 ;
   _ltp1 = ( tau2 * tau1 ) / ( tau1 - tau2 ) * log ( tau1 / tau2 ) ;
   factor1 = - exp ( - _ltp1 / tau2 ) + exp ( - _ltp1 / tau1 ) ;
   factor1 = 1.0 / factor1 ;
   _ltp2 = ( tau4 * tau3 ) / ( tau3 - tau4 ) * log ( tau3 / tau4 ) ;
   factor2 = - exp ( - _ltp2 / tau4 ) + exp ( - _ltp2 / tau3 ) ;
   factor2 = 1.0 / factor2 ;
   }
 
}
}

void nrn_init(NrnThread* _nt, Memb_list* _ml, int _type){
double* _p; Datum* _ppvar; ThreadDatum* _thread;
double _v, v; int* _ni; int _iml, _cntml_padded, _cntml_actual;
    _ni = _ml->_nodeindices;
_cntml_actual = _ml->_nodecount;
_cntml_padded = _ml->_nodecount_padded;
_thread = _ml->_thread;
  assert(_ml->global_variables);
  assert(_ml->global_variables_size != 0);
  _initlists(_ml);
  _update_global_variables(_nt, _ml);
double * _nt_data = _nt->_data;
double * _vec_v = _nt->_actual_v;
int stream_id = _nt->stream_id;
  if (_nrn_skip_initmodel == 0) {
#if LAYOUT == 1 /*AoS*/
for (_iml = 0; _iml < _cntml_actual; ++_iml) {
 _p = _ml->_data + _iml*_psize; _ppvar = _ml->_pdata + _iml*_ppsize;
#elif LAYOUT == 0 /*SoA*/
 _p = _ml->_data; _ppvar = _ml->_pdata;
/* insert compiler dependent ivdep like pragma */
_PRAGMA_FOR_VECTOR_LOOP_
_PRAGMA_FOR_INIT_ACC_LOOP_
for (_iml = 0; _iml < _cntml_actual; ++_iml) {
#else /* LAYOUT > 1 */ /*AoSoA*/
#error AoSoA not implemented.
for (;;) { /* help clang-format properly indent */
#endif
    int _nd_idx = _ni[_iml];
 _tsav = -1e20;
    _v = _vec_v[_nd_idx];
    _PRCELLSTATE_V
 v = _v;
 _PRCELLSTATE_V
 initmodel(_threadargs_);
}
  }
}

static double _nrn_current(_threadargsproto_, double _v){double _current=0.;v=_v;{ {
   double _lcount ;
 gnmda = ( A - B ) / ( 1.0 + n * exp ( - gama * v ) ) ;
   gampa = ( C - D ) ;
   inmda = ( 1e-3 ) * gnmda * ( v - e ) ;
   iampa = ( 1e-3 ) * gampa * ( v - e ) ;
   }
 _current += inmda;
 _current += iampa;

} return _current;
}

#if defined(ENABLE_CUDA_INTERFACE) && defined(_OPENACC)
  void nrn_state_launcher(NrnThread*, Memb_list*, int, int);
  void nrn_jacob_launcher(NrnThread*, Memb_list*, int, int);
  void nrn_cur_launcher(NrnThread*, Memb_list*, int, int);
#endif


void nrn_cur(NrnThread* _nt, Memb_list* _ml, int _type) {
double* _p; Datum* _ppvar; ThreadDatum* _thread;
int* _ni; double _rhs, _g, _v, v; int _iml, _cntml_padded, _cntml_actual;
    _ni = _ml->_nodeindices;
_cntml_actual = _ml->_nodecount;
_cntml_padded = _ml->_nodecount_padded;
_thread = _ml->_thread;
double * _vec_rhs = _nt->_actual_rhs;
double * _vec_d = _nt->_actual_d;
double * _vec_shadow_rhs = _nt->_shadow_rhs;
double * _vec_shadow_d = _nt->_shadow_d;

#if defined(ENABLE_CUDA_INTERFACE) && defined(_OPENACC) && !defined(DISABLE_OPENACC)
  NrnThread* d_nt = cnrn_target_deviceptr(_nt);
  Memb_list* d_ml = cnrn_target_deviceptr(_ml);
  nrn_cur_launcher(d_nt, d_ml, _type, _cntml_actual);
  return;
#endif

double * _nt_data = _nt->_data;
double * _vec_v = _nt->_actual_v;
int stream_id = _nt->stream_id;
#if LAYOUT == 1 /*AoS*/
for (_iml = 0; _iml < _cntml_actual; ++_iml) {
 _p = _ml->_data + _iml*_psize; _ppvar = _ml->_pdata + _iml*_ppsize;
#elif LAYOUT == 0 /*SoA*/
 _p = _ml->_data; _ppvar = _ml->_pdata;
/* insert compiler dependent ivdep like pragma */
_PRAGMA_FOR_VECTOR_LOOP_
_PRAGMA_FOR_CUR_SYN_ACC_LOOP_
for (_iml = 0; _iml < _cntml_actual; ++_iml) {
#else /* LAYOUT > 1 */ /*AoSoA*/
#error AoSoA not implemented.
for (;;) { /* help clang-format properly indent */
#endif
    int _nd_idx = _ni[_iml];
    _v = _vec_v[_nd_idx];
    _PRCELLSTATE_V
 _g = _nrn_current(_threadargs_, _v + .001);
 	{ _rhs = _nrn_current(_threadargs_, _v);
 	}
 _g = (_g - _rhs)/.001;
 double _mfact =  1.e2/(_nd_area);
 _g *=  _mfact;
 _rhs *= _mfact;
 _PRCELLSTATE_G


#ifdef _OPENACC
  if(_nt->compute_gpu) {
    #pragma acc atomic update
    _vec_rhs[_nd_idx] -= _rhs;
    #pragma acc atomic update
    _vec_d[_nd_idx] += _g;
  } else {
    _vec_shadow_rhs[_iml] = _rhs;
    _vec_shadow_d[_iml] = _g;
  }
#else
  _vec_shadow_rhs[_iml] = _rhs;
  _vec_shadow_d[_iml] = _g;
#endif
 }
#ifdef _OPENACC
    if(!(_nt->compute_gpu)) { 
        for (_iml = 0; _iml < _cntml_actual; ++_iml) {
           int _nd_idx = _ni[_iml];
           _vec_rhs[_nd_idx] -= _vec_shadow_rhs[_iml];
           _vec_d[_nd_idx] += _vec_shadow_d[_iml];
        }
#else
 for (_iml = 0; _iml < _cntml_actual; ++_iml) {
   int _nd_idx = _ni[_iml];
   _vec_rhs[_nd_idx] -= _vec_shadow_rhs[_iml];
   _vec_d[_nd_idx] += _vec_shadow_d[_iml];
#endif
 
}
 
}

void nrn_state(NrnThread* _nt, Memb_list* _ml, int _type) {
double* _p; Datum* _ppvar; ThreadDatum* _thread;
double v, _v = 0.0; int* _ni; int _iml, _cntml_padded, _cntml_actual;
    _ni = _ml->_nodeindices;
_cntml_actual = _ml->_nodecount;
_cntml_padded = _ml->_nodecount_padded;
_thread = _ml->_thread;

#if defined(ENABLE_CUDA_INTERFACE) && defined(_OPENACC) && !defined(DISABLE_OPENACC)
  NrnThread* d_nt = cnrn_target_deviceptr(_nt);
  Memb_list* d_ml = cnrn_target_deviceptr(_ml);
  nrn_state_launcher(d_nt, d_ml, _type, _cntml_actual);
  return;
#endif

double * _nt_data = _nt->_data;
double * _vec_v = _nt->_actual_v;
int stream_id = _nt->stream_id;
#if LAYOUT == 1 /*AoS*/
for (_iml = 0; _iml < _cntml_actual; ++_iml) {
 _p = _ml->_data + _iml*_psize; _ppvar = _ml->_pdata + _iml*_ppsize;
#elif LAYOUT == 0 /*SoA*/
 _p = _ml->_data; _ppvar = _ml->_pdata;
/* insert compiler dependent ivdep like pragma */
_PRAGMA_FOR_VECTOR_LOOP_
_PRAGMA_FOR_STATE_ACC_LOOP_
for (_iml = 0; _iml < _cntml_actual; ++_iml) {
#else /* LAYOUT > 1 */ /*AoSoA*/
#error AoSoA not implemented.
for (;;) { /* help clang-format properly indent */
#endif
    int _nd_idx = _ni[_iml];
    _v = _vec_v[_nd_idx];
    _PRCELLSTATE_V
 v=_v;
{
 {   state(_threadargs_);
  }}}

}

static void terminal(){}

static void _initlists(Memb_list *_ml){
 double _x; double* _p = &_x;
 int _i;
 int _cntml_actual=1;
 int _cntml_padded=1;
 int _iml=0;
 _slist1[0] = &(A) - _p;  _dlist1[0] = &(DA) - _p;
 _slist1[1] = &(B) - _p;  _dlist1[1] = &(DB) - _p;
 _slist1[2] = &(C) - _p;  _dlist1[2] = &(DC) - _p;
 _slist1[3] = &(D) - _p;  _dlist1[3] = &(DD) - _p;
 _slist1[4] = &(dampa) - _p;  _dlist1[4] = &(Ddampa) - _p;
 _slist1[5] = &(dnmda) - _p;  _dlist1[5] = &(Ddnmda) - _p;
 _slist1[6] = &(fampa) - _p;  _dlist1[6] = &(Dfampa) - _p;
 _slist1[7] = &(fnmda) - _p;  _dlist1[7] = &(Dfnmda) - _p;
 }
} // namespace coreneuron_lib
