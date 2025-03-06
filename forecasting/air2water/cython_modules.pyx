# air2water_module.pyx
cimport cython
from libc.math cimport exp, cos, ceil
import sys

@cython.boundscheck(False)
@cython.wraparound(False)

def loop_a2w(Tw_solution, Ta_data, tt, a, Tmin, version):
    cdef double DD, pp
    cdef double epsilon
    if Tw_solution >= Tmin:
        DD = exp(-(Tw_solution - Tmin) / a[3])
    else:
        if version == 8 and a[6]!=0 and a[7]!=0:
            DD = exp((Tw_solution - Tmin) / a[6]) + exp(-(Tw_solution / a[7]))
        elif version in [4, 6] or a[6]==0 or a[7]==0:
            DD = 1
        else:
            print("Cython: Please enter correct model version (4,6,8)")
            sys.exit()

    pp = a[0] + a[1] * Ta_data - a[2] * Tw_solution + a[4] * cos(2 * 3.141592653589793 * (tt - a[5]))

    if DD <= 0:
        DD = 0.01

    K=pp/DD

    return DD, pp, K

def substep_a2w(Ta_data1, Ta_data, DD, pp, lim, a, dt):
    cdef double lmbda, nsub, dTair, ttt
    if DD < 0.01:
         DD = 0.01
    lmbda = (pp/a[3] - a[2])/DD
    pp = -lim/lmbda

    if lmbda <= 0.0 and pp < 1.0:
        nsub = int(1/pp)
        if nsub > 100:
            nsub = 100
        dt = 1.0/nsub
    else:
        dt=1.0
        nsub=1
    dTair = (Ta_data1-Ta_data)/nsub

    ttt = dt/nsub

    return dTair, ttt, nsub, dt

def rk4_air2stream(Tw,Ta,Q,Qmedia,time,a,version):
    cdef double DD, K
    if version == 8 or version == 4:
        DD = (Q/Qmedia) * a[3]
    elif version == 5 or version == 3:
        DD = 0.0
    else:
        DD = 1.0

    if version == 3:
        K = a[0] + a[1]*Ta - a[2]*Tw
    elif version == 5:
        K = a[0] + a[1] * Ta - a[2] * Tw + a[5] * cos(2.0 * 3.141592653589793 * (time - a[6]))
    elif version == 8 or version ==7:
        K = a[0] + a[1] * Ta - a[2] * Tw + (Q/Qmedia)*(a[4] + a[5] * cos(2.0 * 3.141592653589793 * (time - a[6]))  - a[7] * Tw)
        K = K/DD
    elif version == 4:
        K = (a[0] + a[1] * Ta - a[2] * Tw) / DD
    else:
        print("Cython: Please enter correct model version (3,4,5,7,8)")
        sys.exit()

    return DD, K

cdef class Air2WaterSolvercn:
    cdef public double[:] Tw_solution
    cdef public double[:] Ta_data
    cdef public double[:] tt
    cdef public double[:] a
    cdef public double Tmin
    cdef public double version
    cdef public int Nt
    cdef public double dt

    def __init__(self, double[:] Tw_solution, double[:] Ta_data,
    double version,
    double[:] tt, double[:] a, double Tmin, int Nt, double dt):
        self.Tw_solution = Tw_solution
        self.Ta_data = Ta_data
        self.tt = tt
        self.a = a
        self.Tmin = Tmin
        self.Nt = Nt
        self.dt = dt
        self.version = version

    cpdef void solve(self):
        cdef int m

        for m in range(self.Nt-1):

            DD, pp, K = loop_a2w(self.Tw_solution[m],self.Ta_data[m],self.tt[m],self.a,self.Tmin, self.version)

            self.Tw_solution[m + 1] = self.Tw_solution[m] * 2.0 * DD + self.dt * (
                        pp + self.a[0] + self.a[1] * self.Ta_data[m + 1] + self.a[4] * cos(2 * 3.141592653589793 * (self.tt[m + 1] - self.a[5])))
            self.Tw_solution[m + 1] = self.Tw_solution[m + 1] / (2 * DD + self.dt * self.a[2])
        if self.Tw_solution[m + 1] < 0:
            self.Tw_solution[m + 1] = 0

cdef class Air2waterSolvereuler(Air2WaterSolvercn):
    cdef public double CFL

    def __init__(self, double[:] Tw_solution, double[:] Ta_data, double version, double CFL,
                 double[:] tt, double[:] a, double Tmin, int Nt, double dt):
        self.CFL=CFL
        super().__init__(Tw_solution, Ta_data, version, tt, a, Tmin, Nt, dt)

    cpdef void solve(self):
        cdef int m,k
        cdef double lim
        cdef double Tairk
        cdef double Twatk
        lim = 2.0 * self.CFL

        for m in range(self.Nt-1):

            DD, pp, K1 = loop_a2w(self.Tw_solution[m],self.Ta_data[m],self.tt[m],self.a,self.Tmin, self.version)
            dTair, ttt, nsub, self.dt = substep_a2w(self.Ta_data[m+1], self.Ta_data[m], DD, pp, lim, self.a, self.dt)

            Twatk = self.Tw_solution[m]
            for k in range(nsub):
                Tairk = self.Ta_data[m] + dTair*(k-1)
                Tairk1 = Tairk + dTair
                ttk= self.tt[m] + ttt * (k-1)

                DD, pp, K1 = loop_a2w(Twatk,0.5*(Tairk+Tairk1),ttk,self.a,self.Tmin, self.version)

                Twatk += K1*self.dt


                self.Tw_solution[m+1] = Twatk

            if self.Tw_solution[m + 1] < 0:
                self.Tw_solution[m + 1] = 0

cdef class Air2waterSolverrk2(Air2WaterSolvercn):
    cdef public double CFL

    def __init__(self, double[:] Tw_solution, double[:] Ta_data, double version, double CFL,
                 double[:] tt, double[:] a, double Tmin, int Nt, double dt):
        self.CFL=CFL
        super().__init__(Tw_solution, Ta_data, version, tt, a, Tmin, Nt, dt)

    cpdef void solve(self):
        cdef int m,k
        cdef double lim
        cdef double Tairk
        cdef double Twatk
        lim = 2.0 * self.CFL

        for m in range(self.Nt-1):

            DD, pp, K1 = loop_a2w(self.Tw_solution[m],self.Ta_data[m],self.tt[m],self.a,self.Tmin, self.version)
            dTair, ttt, nsub, self.dt = substep_a2w(self.Ta_data[m+1], self.Ta_data[m], DD, pp, lim, self.a, self.dt)

            Twatk = self.Tw_solution[m]
            for k in range(nsub):
                Tairk = self.Ta_data[m] + dTair*(k-1)
                Tairk1 = Tairk + dTair
                ttk= self.tt[m] + ttt * (k-1)

                DD, pp, K1 = loop_a2w(Twatk,Tairk,ttk,self.a,self.Tmin, self.version)
                DD, pp, K2 = loop_a2w(Twatk + K1, Tairk1, ttk + ttt, self.a, self.Tmin, self.version)

                Twatk += 0.5*(K1+K2)*self.dt


                self.Tw_solution[m+1] = Twatk

            if self.Tw_solution[m + 1] < 0:
                self.Tw_solution[m + 1] = 0

cdef class Air2waterSolverrk4(Air2WaterSolvercn):
    cdef public double CFL

    def __init__(self, double[:] Tw_solution, double[:] Ta_data, double version, double CFL,
                 double[:] tt, double[:] a, double Tmin, int Nt, double dt):
        self.CFL=CFL
        super().__init__(Tw_solution, Ta_data, version, tt, a, Tmin, Nt, dt)

    cpdef void solve(self):
        cdef int m,k
        cdef double lim
        cdef double Tairk
        cdef double Twatk
        lim = 2.785 * self.CFL

        for m in range(self.Nt-1):

            DD, pp, K1 = loop_a2w(self.Tw_solution[m],self.Ta_data[m],self.tt[m],self.a,self.Tmin, self.version)
            dTair, ttt, nsub, self.dt = substep_a2w(self.Ta_data[m+1], self.Ta_data[m], DD, pp, lim, self.a, self.dt)

            Twatk = self.Tw_solution[m]
            for k in range(nsub):
                Tairk = self.Ta_data[m] + dTair*(k-1)
                Tairk1 = Tairk + dTair
                ttk= self.tt[m] + ttt * (k-1)

                DD, pp, K1 = loop_a2w(Twatk,Tairk,ttk,self.a,self.Tmin, self.version)
                DD, pp, K2 = loop_a2w(Twatk + 0.5*K1, 0.5*(Tairk+Tairk1), ttk+0.5*ttt, self.a, self.Tmin, self.version)
                DD, pp, K3 = loop_a2w(Twatk + 0.5*K2, 0.5*(Tairk+Tairk1), ttk+0.5*ttt, self.a, self.Tmin, self.version)
                DD, pp, K4 = loop_a2w(Twatk + K3, Tairk1, ttk + ttt, self.a, self.Tmin, self.version)

                Twatk += (1/6)*(K1+2*K2+2*K3+K4)*self.dt


                self.Tw_solution[m+1] = Twatk

            if self.Tw_solution[m + 1] < 0:
                self.Tw_solution[m + 1] = 0


cdef class Air2StreamSolvercn(Air2WaterSolvercn):
    cdef public double[:] Q
    cdef public double Qmedia

    def __init__(self, double[:] Tw_solution, double[:] Ta_data, double[:] Q, double Qmedia, double version,
                 double[:] tt, double[:] a, double Tmin, int Nt, double dt):
        super().__init__(Tw_solution, Ta_data, version, tt, a, Tmin, Nt, dt)
        self.Q = Q
        self.Qmedia = Qmedia

    cpdef void solve(self):
        cdef int m
        cdef double theta_j, theta_j1, DD_j, DD_j1, pp

        for m in range(self.Nt-1):
            if self.version in [4,7,8]:
                theta_j = self.Q[m] / (self.Qmedia)
                theta_j1 = self.Q[m + 1] / (self.Qmedia)
                DD_j = theta_j ** self.a[3]
                DD_j1 = theta_j1 ** self.a[3]
                pp = self.a[0] + self.a[1] * self.Ta_data[m] - self.a[2] * self.Tw_solution[m] + theta_j * (
                            self.a[4] + self.a[5] * cos(2 * 3.141592653589793 * (self.tt[m] - self.a[6])) - self.a[7] * self.Tw_solution[m])

                self.Tw_solution[m + 1] = (self.Tw_solution[m] + 0.5 / DD_j * pp + 0.5 / DD_j1 * (
                            self.a[0] + self.a[1] * self.Ta_data[m + 1] + theta_j1 * (
                                        self.a[4] + self.a[5] * cos(2 * 3.141592653589793 * (self.tt[m + 1] - self.a[6]))))) / (
                                                          1.0 + 0.5 * self.a[7] * theta_j1 / DD_j1 + 0.5 * self.a[2] / DD_j1)
            elif self.version in [3,5]:
                self.Tw_solution[m + 1] = (self.Tw_solution[m] * (1.0 - 0.5 * self.a[2]) + self.a[0] + 0.5 * self.a[1] * (self.Ta_data[m] + self.Ta_data[m + 1]) + 0.5 * self.a[5] * cos(2 * 3.141592653589793 * (self.tt[m] - self.a[6])) + 0.5 * self.a[5] * cos(2 * 3.141592653589793 * (self.tt[m+1] - self.a[6]))) / (1.0 + 0.5 * self.a[2])

            else:
                print("Cython: Please enter correct model version (3,4,5,7,8)")
                sys.exit()

        if self.Tw_solution[m + 1] < 0:
            self.Tw_solution[m + 1] = 0

cdef class Air2StreamSolvereuler(Air2StreamSolvercn):

    def __init__(self, double[:] Tw_solution, double[:] Ta_data, double[:] Q, double Qmedia, double version,
                 double[:] tt, double[:] a, double Tmin, int Nt, double dt):
        super().__init__(Tw_solution, Ta_data, Q, Qmedia, version, tt, a, Tmin, Nt, dt)

    cpdef void solve(self):
        cdef int m
        for m in range(self.Nt-1):
            DD, K1= rk4_air2stream(self.Tw_solution[m],self.Ta_data[m+1],self.Q[m+1],self.Qmedia,self.tt[m+1],self.a,self.version)
            self.Tw_solution[m+1] = self.Tw_solution[m] + K1

        if self.Tw_solution[m + 1] < 0:
            self.Tw_solution[m + 1] = 0

cdef class Air2StreamSolverrk2(Air2StreamSolvercn):

    def __init__(self, double[:] Tw_solution, double[:] Ta_data, double[:] Q, double Qmedia, double version,
                 double[:] tt, double[:] a, double Tmin, int Nt, double dt):
        super().__init__(Tw_solution, Ta_data, Q, Qmedia, version, tt, a, Tmin, Nt, dt)

    cpdef void solve(self):
        cdef int m
        for m in range(self.Nt-1):
            DD, K1= rk4_air2stream(self.Tw_solution[m],self.Ta_data[m],self.Q[m],self.Qmedia,self.tt[m],self.a,self.version)
            DD, K2= rk4_air2stream(self.Tw_solution[m]+K1,self.Ta_data[m+1],self.Q[m+1],self.Qmedia,self.tt[m] + (1/366) ,self.a,self.version)
            self.Tw_solution[m+1] = self.Tw_solution[m] + 0.5 * (K1+K2)

        if self.Tw_solution[m + 1] < 0:
            self.Tw_solution[m + 1] = 0

cdef class Air2StreamSolverrk4(Air2StreamSolvercn):

    def __init__(self, double[:] Tw_solution, double[:] Ta_data, double[:] Q, double Qmedia, double version,
                 double[:] tt, double[:] a, double Tmin, int Nt, double dt):
        super().__init__(Tw_solution, Ta_data, Q, Qmedia, version, tt, a, Tmin, Nt, dt)

    cpdef void solve(self):
        cdef int m
        for m in range(self.Nt-1):
            DD, K1= rk4_air2stream(self.Tw_solution[m],self.Ta_data[m],self.Q[m],self.Qmedia,self.tt[m],self.a,self.version)
            DD, K2= rk4_air2stream(self.Tw_solution[m]+0.5*K1,0.5*(self.Ta_data[m]+self.Ta_data[m+1]),0.5*(self.Q[m]+self.Q[m+1]),self.Qmedia,self.tt[m]+ (0.5/366) ,self.a,self.version)
            DD, K3= rk4_air2stream(self.Tw_solution[m]+0.5*K2,0.5*(self.Ta_data[m]+self.Ta_data[m+1]),0.5*(self.Q[m]+self.Q[m+1]),self.Qmedia,self.tt[m]+ (0.5/366) ,self.a,self.version)
            DD, K4= rk4_air2stream(self.Tw_solution[m]+K3,self.Ta_data[m+1],self.Q[m+1],self.Qmedia,self.tt[m]+ (1/366) ,self.a,self.version)
            self.Tw_solution[m+1] = self.Tw_solution[m] + (1/6) * (K1+2*K2+2*K3+K4)

        if self.Tw_solution[m + 1] < 0:
            self.Tw_solution[m + 1] = 0