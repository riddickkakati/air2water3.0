subroutine loop_a2w(Tw_solution, Ta_data, tt, a, Tmin, version, DD, pp, K)
    implicit none
    REAL(KIND=8), intent(in) :: Tw_solution, Ta_data, tt, a(8), Tmin
    integer, intent(in) :: version
    REAL(KIND=8) :: DD, pp, K

    if (Tw_solution >= Tmin) then
        DD = exp(-(Tw_solution - Tmin) / a(4))
    else
        if (version == 8 .and. a(7) /= 0 .and. a(8) /= 0) then
            DD = exp((Tw_solution - Tmin) / a(7)) + exp(-(Tw_solution / a(8)))
        elseif (version == 4 .or. version == 6 .or. a(7) == 0 .or. a(8) == 0) then
            DD = 1.0
        else
            write(*, *) 'Fortran: Please enter correct model version (4,6,8)'
            stop
        end if
    end if

    pp = a(1) + a(2) * Ta_data - a(3) * Tw_solution + a(5) * cos(2.0 * 3.141592653589793d0 * (tt - a(6)))

    if (DD <= 0.0d0) then
        DD = 0.01d0
    end if

    K = pp / DD
end subroutine loop_a2w

subroutine substep_a2w(Ta_data1, Ta_data, DD, pp, lim, a, dt, dTair, ttt, nsub)
    implicit none
    REAL(KIND=8), intent(in) :: Ta_data1, Ta_data, lim, a(8)
    REAL(KIND=8) :: lmbda, dTair, ttt, DD, pp, dt
    integer :: nsub

    if (DD < 0.01d0) then
        DD = 0.01d0
    end if

    lmbda = (pp / a(4) - a(3)) / DD
    pp = -lim / lmbda

    if (lmbda <= 0.0d0 .and. pp < 1.0d0) then
        nsub = min(100, int(1.0d0 / pp))
        dt = 1.0d0 / nsub
    else
        dt = 1.0d0
        nsub = 1
    end if

    dTair = (Ta_data1 - Ta_data) / real(nsub)
    ttt = dt / real(nsub)
end subroutine substep_a2w

subroutine rk4_air2stream(Tw, Ta, Q, Qmedia, time, a, version, DD, K)
    implicit none
    REAL(KIND=8), intent(in) :: Tw, Ta, Q, Qmedia, time, a(8)
    integer, intent(in) :: version
    REAL(KIND=8) :: DD, K

    if (version == 8 .or. version == 4) then
        DD = (Q / Qmedia) * a(4)
    elseif (version == 5 .or. version == 3) then
        DD = 0.0d0
    else
        DD = 1.0d0
    end if

    if (version == 3) then
        K = a(1) + a(2) * Ta - a(3) * Tw
    elseif (version == 5) then
        K = a(1) + a(2) * Ta - a(3) * Tw + a(6) * cos(2.0d0 * 3.141592653589793d0 * (time - a(7)))
    elseif (version == 8 .or. version == 7) then
        K = a(1) + a(2) * Ta - a(3) * Tw + &
    (Q / Qmedia) * (a(5) + a(6) * cos(2.0d0 * 3.141592653589793d0 * (time - a(7))) - a(8) * Tw)
        K = K / DD
    elseif (version == 4) then
        K = (a(1) + a(2) * Ta - a(3) * Tw) / DD
    else
        write(*, *) 'Fortran: Please enter correct model version (3,4,5,7,8)'
        stop
    end if
end subroutine rk4_air2stream

subroutine air2watercn_loop(Tw_solution, Ta_data, version, tt, a, Tmin, Nt, dt)
    implicit none
    integer, intent(in) :: Nt
    REAL(KIND=8), intent(in) :: Tmin, dt
    REAL(KIND=8), intent(in) :: Ta_data(Nt), tt(Nt), a(8)
    REAL(KIND=8), intent(inout) :: Tw_solution(Nt)
    integer :: m, version
    REAL(KIND=8) :: DD, pp, K

    do m = 1, Nt - 1
        call loop_a2w(Tw_solution(m), Ta_data(m), tt(m), a, Tmin, version, DD, pp, K)
        Tw_solution(m + 1) = Tw_solution(m) * 2.0 * DD + dt * ( &
                    pp + a(1) + a(2) * Ta_data(m + 1) + a(5) * cos(2.0 * 3.141592653589793 * (tt(m + 1) - a(6))))
        Tw_solution(m + 1) = Tw_solution(m + 1) / (2.0 * DD + dt * a(3))
        if (Tw_solution(m + 1) < 0) then
            Tw_solution(m + 1) = 0
        endif
    end do

end subroutine air2watercn_loop

subroutine air2watereuler_loop(Tw_solution, Ta_data, version, CFL, tt, a, Tmin, Nt, dt)
    implicit none
    integer, intent(in) :: Nt
    REAL(KIND=8), intent(in) :: Tmin, dt
    REAL(KIND=8), intent(in) :: Ta_data(Nt), tt(Nt), a(8)
    REAL(KIND=8), intent(inout) :: Tw_solution(Nt)
    integer :: m, version, nsub, k
    REAL(KIND=8) :: DD, pp, K1, CFL, lim, dTair, ttt, Tairk, Tairk1, Twatk, ttk

    lim = 2.0d0 * CFL

    do m = 1, Nt - 1
        call loop_a2w(Tw_solution(m), Ta_data(m), tt(m), a, Tmin, version, DD, pp, K1)
        call substep_a2w(Ta_data(m + 1), Ta_data(m), DD, pp, lim, a, dt, dTair, ttt, nsub)

        Twatk = Tw_solution(m)
        do k = 1, nsub
            Tairk = Ta_data(m) + dTair * (k - 1)
            Tairk1 = Tairk + dTair
            ttk = tt(m) + ttt * (k - 1)

            call loop_a2w(Twatk, 0.5*(Tairk+Tairk1), ttk, a, Tmin, version, DD, pp, K1)

            Twatk = Twatk + K1 * dt
        end do

        if (Twatk < 0.0d0) Twatk = 0.0d0

        Tw_solution(m + 1) = Twatk
    end do
end subroutine air2watereuler_loop

subroutine air2waterrk2_loop(Tw_solution, Ta_data, version, CFL, tt, a, Tmin, Nt, dt)
    implicit none
    integer, intent(in) :: Nt
    REAL(KIND=8), intent(in) :: Tmin, dt
    REAL(KIND=8), intent(in) :: Ta_data(Nt), tt(Nt), a(8)
    REAL(KIND=8), intent(inout) :: Tw_solution(Nt)
    integer :: m, version, nsub, k
    REAL(KIND=8) :: DD, pp, K1, K2, CFL, lim, dTair, ttt, Tairk, Tairk1, Twatk, ttk

    lim = 2.0d0 * CFL

    do m = 1, Nt - 1
        call loop_a2w(Tw_solution(m), Ta_data(m), tt(m), a, Tmin, version, DD, pp, K1)
        call substep_a2w(Ta_data(m + 1), Ta_data(m), DD, pp, lim, a, dt, dTair, ttt, nsub)

        Twatk = Tw_solution(m)
        do k = 1, nsub
            Tairk = Ta_data(m) + dTair * (k - 1)
            Tairk1 = Tairk + dTair
            ttk = tt(m) + ttt * (k - 1)

            call loop_a2w(Twatk, Tairk, ttk, a, Tmin, version, DD, pp, K1)
            call loop_a2w(Twatk + K1, Tairk1, ttk+ttt, a, Tmin, version, DD, pp, K2)

            Twatk = Twatk + 0.5* (K1 + K2) * dt
        end do

        if (Twatk < 0.0d0) Twatk = 0.0d0

        Tw_solution(m + 1) = Twatk
    end do
end subroutine air2waterrk2_loop

subroutine air2waterrk4_loop(Tw_solution, Ta_data, version, CFL, tt, a, Tmin, Nt, dt)
    implicit none
    integer, intent(in) :: Nt
    REAL(KIND=8), intent(in) :: Tmin, dt
    REAL(KIND=8), intent(in) :: Ta_data(Nt), tt(Nt), a(8)
    REAL(KIND=8), intent(inout) :: Tw_solution(Nt)
    integer :: m, version, nsub, k
    REAL(KIND=8) :: DD, pp, K1, K2, K3, K4, CFL, lim, dTair, ttt, Tairk, Tairk1, Twatk, ttk

    lim = 2.0d0 * CFL

    do m = 1, Nt - 1
        call loop_a2w(Tw_solution(m), Ta_data(m), tt(m), a, Tmin, version, DD, pp, K1)
        call substep_a2w(Ta_data(m + 1), Ta_data(m), DD, pp, lim, a, dt, dTair, ttt, nsub)

        Twatk = Tw_solution(m)
        do k = 1, nsub
            Tairk = Ta_data(m) + dTair * (k - 1)
            Tairk1 = Tairk + dTair
            ttk = tt(m) + ttt * (k - 1)

            call loop_a2w(Twatk, Tairk, ttk, a, Tmin, version, DD, pp, K1)
            call loop_a2w(Twatk + 0.5*K1, 0.5*(Tairk+Tairk1), ttk + 0.5 * ttt, a, Tmin, version, DD, pp, K2)
            call loop_a2w(Twatk + 0.5*K2, 0.5*(Tairk+Tairk1), ttk + 0.5 * ttt, a, Tmin, version, DD, pp, K3)
            call loop_a2w(Twatk + K3, Tairk1, ttk + ttt, a, Tmin, version, DD, pp, K4)

            Twatk = Twatk + (1/6)* (K1 + 2*K2 + 2*K3 + k4) * dt
        end do

        if (Twatk < 0.0d0) Twatk = 0.0d0

        Tw_solution(m + 1) = Twatk
    end do
end subroutine air2waterrk4_loop

subroutine air2streamcn_loop(Tw_solution, Ta_data, Q, Qmedia, version, tt, a, Tmin, Nt, dt)
    implicit none
    integer, intent(in) :: Nt
    REAL(KIND=8), intent(in) :: Tmin, dt, version
    REAL(KIND=8), intent(in) :: Ta_data(Nt), Q(Nt), Qmedia, tt(Nt), a(8)
    REAL(KIND=8), intent(inout) :: Tw_solution(Nt)
    integer :: m
    REAL(KIND=8) :: theta_j, theta_j1, DD_j, DD_j1, pp

    do m = 1, Nt - 1
        if (version==8 .or. version==7 .or. version==4) then
            theta_j = Q(m) / Qmedia
            theta_j1 = Q(m + 1) / Qmedia
            DD_j = theta_j ** a(4)
            DD_j1 = theta_j1 ** a(4)
            pp = a(1) + a(2) * Ta_data(m) - a(3) * Tw_solution(m) + theta_j * ( &
                a(5) + a(6) * cos(2.0 * 3.141592653589793 * (tt(m) - a(7))) - a(8) * Tw_solution(m))

            Tw_solution(m + 1) = (Tw_solution(m) + 0.5 / DD_j * pp + 0.5 / DD_j1 * ( &
                a(1) + a(2) * Ta_data(m+1) + theta_j1 * (a(5) + a(6) * cos(2.0 * 3.141592653589793 * (tt(m + 1) - a(7)))))) / ( &
                1.0 + 0.5 * a(8) * theta_j1 / DD_j1 + 0.5 * a(3) / DD_j1)
        else if (version==5 .or. version==3) then

            Tw_solution(m + 1) = (Tw_solution(m) * (1.0 - 0.5 * a(3)) + &
                            a(1) + 0.5 * a(2) * (Ta_data(m) + Ta_data(m + 1)) + &
                            0.5 * a(6) * cos(2.0 * 3.141592653589793 * (tt(m) - a(7))) + &
                            0.5 * a(6) * cos(2.0 * 3.141592653589793 * (tt(m + 1) - a(7)))) / &
                            (1.0 + 0.5 * a(3));

        else
                    write(*, *) 'Fortran: Please enter correct model version (4,6,8)'
                    stop
        end if
        if (Tw_solution(m + 1) < 0) then
            Tw_solution(m + 1) = 0
        endif
    end do

end subroutine air2streamcn_loop

subroutine air2streameuler_loop(Tw_solution, Ta_data, Q, Qmedia, version, tt, a, Tmin, Nt, dt)
    implicit none
    integer, intent(in) :: Nt, version
    REAL(KIND=8), intent(in) :: Tmin, dt
    REAL(KIND=8), intent(in) :: Ta_data(Nt), Q(Nt), Qmedia, tt(Nt), a(8)
    REAL(KIND=8), intent(inout) :: Tw_solution(Nt)
    integer :: m
    REAL(KIND=8) :: pp, DD, K1

    do m = 1, Nt - 1
         call rk4_air2stream(Tw_solution(m), Ta_data(m + 1), Q(m + 1), Qmedia, tt(m + 1), a, &
                            version, DD, K1)
         Tw_solution(m + 1) = Tw_solution(m) + K1

         if (Tw_solution(m + 1) < 0.0d0) Tw_solution(m + 1) = 0.0d0
    end do

end subroutine air2streameuler_loop

subroutine air2streamrk2_loop(Tw_solution, Ta_data, Q, Qmedia, version, tt, a, Tmin, Nt, dt)
    implicit none
    integer, intent(in) :: Nt, version
    REAL(KIND=8), intent(in) :: Tmin, dt
    REAL(KIND=8), intent(in) :: Ta_data(Nt), Q(Nt), Qmedia, tt(Nt), a(8)
    REAL(KIND=8), intent(inout) :: Tw_solution(Nt)
    integer :: m
    REAL(KIND=8) :: pp, DD, K1, K2

    do m = 1, Nt - 1
         call rk4_air2stream(Tw_solution(m), Ta_data(m), Q(m), Qmedia, tt(m), a, &
                            version, DD, K1)
         call rk4_air2stream(Tw_solution(m)+K1, Ta_data(m+1), Q(m+1), Qmedia, tt(m) + (1/366), a, &
                            version, DD, K2)
         Tw_solution(m + 1) = Tw_solution(m) + 0.5*(K1+K2)

         if (Tw_solution(m + 1) < 0.0d0) Tw_solution(m + 1) = 0.0d0
    end do

end subroutine air2streamrk2_loop

subroutine air2streamrk4_loop(Tw_solution, Ta_data, Q, Qmedia, version, tt, a, Tmin, Nt, dt)
    implicit none
    integer, intent(in) :: Nt, version
    REAL(KIND=8), intent(in) :: Tmin, dt
    REAL(KIND=8), intent(in) :: Ta_data(Nt), Q(Nt), Qmedia, tt(Nt), a(8)
    REAL(KIND=8), intent(inout) :: Tw_solution(Nt)
    integer :: m
    REAL(KIND=8) :: pp, DD, K1, K2, K3, K4

    do m = 1, Nt - 1
         call rk4_air2stream(Tw_solution(m), Ta_data(m), Q(m), Qmedia, tt(m), a, &
                            version, DD, K1)
         call rk4_air2stream(Tw_solution(m)+ 0.5 * K1, 0.5 * (Ta_data(m) + Ta_data(m+1)), &
          0.5 * (Q(m) + Q(m+1)), Qmedia, tt(m) + (0.5/366), a, &
                            version, DD, K2)
         call rk4_air2stream(Tw_solution(m)+ 0.5 * K2, 0.5 * (Ta_data(m) + Ta_data(m+1)), &
         0.5 * (Q(m) + Q(m+1)), Qmedia, tt(m) + (0.5/366), a, &
                            version, DD, K3)
         call rk4_air2stream(Tw_solution(m)+ K3, Ta_data(m+1), Q(m+1), Qmedia, tt(m) + (1/366), a, &
                            version, DD, K4)
         Tw_solution(m + 1) = Tw_solution(m) + (1/6)*(K1+2*K2+2*K3+K4)

         if (Tw_solution(m + 1) < 0.0d0) Tw_solution(m + 1) = 0.0d0
    end do

end subroutine air2streamrk4_loop