from functools import partial
import numpy as np
from forecasting.air2water.calibrators.spotpy_params_air2water_air2stream import spot_setup
import pandas as pd

class pso_oop_new:

    def __init__(self,func,db_file, dbformat, lb,ub, threshold, ieqcons=[], f_ieqcons=None, args=(), kwargs={},
            swarmsize=100, omega=0.5, phip=0.5, phig=0.5, maxiter=100,
            minstep=1e-3, minfunc=1e-3, processes=10,
            particle_output=False,model="air2water"):
        self.func=func
        self.db_file=db_file
        self.dbformat=dbformat
        self.lb=lb
        self.ub=ub
        self.ieqcons=ieqcons
        self.f_ieqcons=f_ieqcons
        self.args=args
        self.kwargs=kwargs
        self.swarmsize=swarmsize
        self.omega=omega
        self.phip=phip
        self.phig=phig
        self.maxiter=maxiter
        self.minstep=minstep
        self.minfunc=minfunc
        #self.debug=debug
        self.processes=processes
        self.particle_output=particle_output
        self.threshold=threshold
        self.model=model

    def _obj_wrapper(self, x):
        return self.func(x, *self.args, **self.kwargs)


    def _is_feasible_wrapper(self, x):
        return np.all(self.func(x) >= 0)


    def _cons_none_wrapper(self, x):
        return np.array([0])


    def _cons_ieqcons_wrapper(self, x):
        return np.array([y(x, self.args, self.kwargs) for y in self.ieqcons])


    def _cons_f_ieqcons_wrapper(self, x):
        return np.array(self.f_ieqcons(x, self.args, self.kwargs))


    def pso(self):
        """
        Perform a particle swarm optimization (PSO)

        Parameters
        ==========
        self.func : function
            The function to be minimized
        self.lb : array
            The lower bounds of the design variable(s)
        self.ub : array
            The upper bounds of the design variable(s)

        Optional
        ========
        self.ieqcons : list
            A list of functions of length n such that self.ieqcons[j](x,*self.args) >= 0.0 in
            a successfully optimized problem (Default: [])
        self.f_ieqcons : function
            Returns a 1-D array in which each element must be greater or equal
            to 0.0 in a successfully optimized problem. If self.f_ieqcons is specified,
            self.ieqcons is ignored (Default: None)
        self.args : tuple
            Additional arguments passed to objective and constraint functions
            (Default: empty tuple)
        self.kwargs : dict
            Additional keyword arguments passed to objective and constraint
            functions (Default: empty dict)
        self.swarmsize : int
            The number of particles in the swarm (Default: 100)
        self.omega : scalar
            Particle velocity scaling factor (Default: 0.5)
        self.phip : scalar
            Scaling factor to search away from the particle's best known position
            (Default: 0.5)
        self.phig : scalar
            Scaling factor to search away from the swarm's best known position
            (Default: 0.5)
        self.maxiter : int
            The maximum number of iterations for the swarm to search (Default: 100)
        self.minstep : scalar
            The minimum stepsize of swarm's best position before the search
            terminates (Default: 1e-8)
        self.minfunc : scalar
            The minimum change of swarm's best objective value before the search
            terminates (Default: 1e-8)
        self.debug : boolean
            If True, progress statements will be displayed every iteration
            (Default: False)
        self.processes : int
            The number of self.processes to use to evaluate objective function and
            constraints (default: 1)
        self.particle_output : boolean
            Whether to include the best per-particle position and the objective
            values at those.

        Returns
        =======
        g : array
            The swarm's best known position (optimal design)
        f : scalar
            The objective value at ``g``
        p : array
            The best known position per particle
        pf: arrray
            The objective values at each position in p

        """
        df3=[]
        spotpyreaderlist=[]
        functioncontrol=0
        assert len(self.lb) == len(self.ub), 'Lower- and upper-bounds must be the same length'
        assert hasattr(self.func, '__call__'), 'Invalid function handle'
        self.lb = np.array(self.lb)
        self.ub = np.array(self.ub)
        assert np.all(self.ub > self.lb), 'All upper-bound values must be greater than lower-bound values'
        df=[]
        vhigh = np.abs(self.ub - self.lb)
        vlow = -vhigh

        # Initialize objective function
        obj = partial(self._obj_wrapper)

        # Check for constraint function(s) #########################################
        if self.f_ieqcons is None:
            if not len(self.ieqcons):
                #if self.debug:
                print('No constraints given.')
                cons = self._cons_none_wrapper
            else:
                #if self.debug:
                print('Converting self.ieqcons to a single constraint function')
                cons = partial(self._cons_ieqcons_wrapper)
        else:
            #if self.debug:
            print('Single constraint function given in self.f_ieqcons')
            cons = partial(self._cons_f_ieqcons_wrapper)
        is_feasible = partial(self._is_feasible_wrapper)

        # Initialize the multiprocessing module if necessary
        if self.processes > 1:
            import multiprocessing
            mp_pool = multiprocessing.Pool(self.processes)

        # Initialize the particle swarm ############################################
        S = self.swarmsize
        D = len(self.lb)  # the number of dimensions each particle has
        x = np.random.rand(S, D)  # particle positions
        v = np.zeros_like(x)  # particle velocities
        p = np.zeros_like(x)  # best particle positions
        fx = np.zeros(S)  # current particle function values
        fs = np.zeros(S, dtype=bool)  # feasibility of each particle
        fp = np.ones(S) * np.inf  # best particle function values
        g = []  # best swarm position
        fg = np.inf  # best swarm position starting value

        # Initialize the particle's position
        x = self.lb + x * (self.ub - self.lb)

        # Calculate objective and constraints for each particle
        if self.processes > 1:
            fx = np.array(mp_pool.map(obj, x))
            fs = np.array(mp_pool.map(is_feasible, x))
        else:
            for i in range(S):
                fx[i] = obj(x[i, :])
                fs[i] = is_feasible(x[i, :])

        # Store particle's best position (if constraints are satisfied)
        i_update = np.logical_and((fx < fp), fs)
        p[i_update, :] = x[i_update, :].copy()
        fp[i_update] = fx[i_update]

        # Update swarm's best position
        i_min = np.argmin(fp)
        if fp[i_min] < fg:
            fg = fp[i_min]
            g = p[i_min, :].copy()
        else:
            # At the start, there may not be any feasible starting point, so just
            # give it a temporary "best" point since it's likely to change
            g = x[0, :].copy()

        # Initialize the particle's velocity
        v = vlow + np.random.rand(S, D) * (vhigh - vlow)

        # Iterate until termination criterion met ##################################
        it = 1
        loop_print=0
        while it <= self.maxiter:

            rp = np.random.uniform(size=(S, D))
            rg = np.random.uniform(size=(S, D))

            model_names=["air2water","air2stream"]

            if self.model in model_names:
                for ja2w in range(len(self.lb)):
                    for ka2w in range(len(x[ja2w])):
                        if x[ja2w][ka2w] > self.ub[ja2w]:
                            if ja2w == 5:
                                x[ja2w][ka2w] = x[ja2w][ka2w] - np.floor(x[ja2w][ka2w])
                            else:
                                x[ja2w][ka2w] = self.ub[ja2w]
                                v[ja2w][ka2w] = 0.0
                        if x[ja2w][ka2w] < self.lb[ja2w]:
                            if ja2w == 5:
                                x[ja2w][ka2w] = np.ceil(np.abs(x[ja2w][ka2w])) - np.abs(x[ja2w][ka2w])
                            else:
                                x[ja2w][ka2w] = self.lb[ja2w]
                                v[ja2w][ka2w] = 0.0

            # Update the particles velocities
            v = self.omega * v + self.phip * rp * (p - x) + self.phig * rg * (g - x)
            # Update the particles' positions
            x = x + v
            # Correct for bound violations
            maskl = x < self.lb
            masku = x > self.ub
            x = x * (~np.logical_or(maskl, masku)) + self.lb * maskl + self.ub * masku

            # Update objectives and constraints
            if self.processes > 1:
                fx = np.array(mp_pool.map(obj, x))
                fs = np.array(mp_pool.map(is_feasible, x))
            else:
                for i in range(S):
                    fx[i] = obj(x[i, :])
                    fs[i] = is_feasible(x[i, :])

            # Store particle's best position (if constraints are satisfied)
            i_update = np.logical_and((fx < fp), fs)
            p[i_update, :] = x[i_update, :].copy()
            fp[i_update] = fx[i_update]

            # Compare swarm's best position with global best position
            i_min = np.argmin(fp)
            if fp[i_min] < fg:
                #if self.debug:
                print('New best for swarm at iteration {:}: {:} {:}' \
                      .format(it, p[i_min, :], fp[i_min]))

                p_min = p[i_min, :].copy()
                stepsize = np.sqrt(np.sum((g - p_min) ** 2))

                if np.abs(fg - fp[i_min]) <= self.minfunc:
                    print('Stopping search: Swarm best objective change less than {:}' \
                          .format(self.minfunc))
                    loop_print=1
                    if self.particle_output:
                        functioncontrol=1
                        a,b,c,d= p_min, fp[i_min], p, fp
                        break;
                    else:
                        functioncontrol=1
                        a,b= p_min, fp[i_min]
                        break;
                elif stepsize <= self.minstep:
                    print('Stopping search: Swarm best position change less than {:}' \
                          .format(self.minstep))
                    loop_print=1
                    if self.particle_output:
                        functioncontrol=1
                        a,b,c,d= p_min, fp[i_min], p, fp
                        break
                    else:
                        functioncontrol=1
                        a,b= p_min, fp[i_min]
                        break
                else:
                    g = p_min.copy()
                    fg = fp[i_min]

            #if self.debug:
            print('Best after iteration {:}: {:} {:}'.format(it, g, fg))
            glist=g.tolist()
            newlist=[]
            newlist.append(fg)
            for number in glist:
                newlist.append(number)
            df3.append(newlist)
            spotpyreaderlist.append(tuple(newlist))
            spot_setup.save(self,fg, g)
            it += 1
        spot_setup.save(self,fg, g)
        glist = g.tolist()
        newlist = []
        newlist.append(fg)
        for number in glist:
            newlist.append(number)
        df3.append(newlist)
        spotpyreaderlist.append(tuple(newlist))
        df3=pd.DataFrame(df3)
        df3size=len(df3.columns)
        df3.columns = ['like1'] + ['par' + str(i) for i in range(1, df3size)]
        generate_list = lambda df3size, dtype='<f8': [('like1', dtype)] + [('para{}'.format(i), dtype) for i in
                                                                              range(1, df3size)]
        dtype = np.dtype(generate_list(df3size))
        spotpyreaderlist=np.array(spotpyreaderlist,dtype=dtype)
        if not loop_print:
            print('Stopping search: maximum iterations reached --> {:}'.format(self.maxiter))

        if not is_feasible(g):
            print("However, the optimization couldn't find a feasible design. Sorry")
        if self.particle_output and functioncontrol==0:
            a=g
            b=fg
            c=p
            d=fp
            #return g, fg, p, fp
        elif not self.particle_output and functioncontrol==0:
            a=g
            b=fg
        if self.dbformat == "ram":
            if self.particle_output:
                return a,b,c,d,df3,spotpyreaderlist
            else:
                return a,b,df3,spotpyreaderlist
        else:
            if self.particle_output:
                return a,b,c,d
            else:
                return a,b