! A set of Fortran routines to quickly carry out compressible flow (method
! of characteristics) calculations in the Hobyah tunnel ventilation program.
! These Fortran routines are copies of existing Python routines but run
! much faster.
!
! Copyright 2020-2024, Ewan Bennett
!
! All rights reserved.
!
! Released under the BSD 2-clause licence (SPDX identifier: BSD-2-Clause)
!
! email: ewanbennett@fastmail.com
!
!
! Command line instructions to compile it:
!    python -m numpy.f2py -c compressible.f95 -m compressible
!
! Should also use the following every now and again to catch bad practice:
!    gfortran -Wall -pedantic compressible.f95
!

function calccelerity1(P, rho, gamma)
  ! Take a pressure, a density and the ratio of specific heats, return the
  ! speed of sound (c) using the expression for speed of sound in a perfect
  ! gas.
  !
  implicit none
  integer, parameter :: dp=kind(0.d0)
  real(dp), intent(in) :: P       ! The air static pressure (Pa)
  real(dp), intent(in) :: rho     ! The air density (kg/m^3)
  real(dp), intent(in) :: gamma   ! Ratio of specific heats, typically 1.4 for
                                  ! air (dimensionless).
  real(dp) :: calccelerity1       ! Speed of sound (m/s)

  calccelerity1 = sqrt(gamma * P / rho)
end function calccelerity1


function calccelerity2(P, P_atm, c_atm, gammapsi)
  ! Take a pressure, a reference pressure, a reference celerity and
  ! a constant in the compressible calculation.
  ! Return the speed of sound at the pressure using the expression for
  ! speed of sound for a reversible isentropic change.
  !
  implicit none
  integer, parameter :: dp=kind(0.d0)
  real(dp), intent(in) :: P        ! The air pressure (Pa)
  real(dp), intent(in) :: P_atm    ! The reference air pressure (Pa)
  real(dp), intent(in) :: c_atm    ! The celerity that matches P_atm (m/s)
  real(dp), intent(in) :: gammapsi ! (gamma - 1) / (2 gamma)
  real(dp) :: calccelerity2        ! Speed of sound (m/s)

  calccelerity2 = c_atm * (P / P_atm)**gammapsi
end function calccelerity2


function Colebrook(rr37, Re)
  ! Calculate the Fanning friction factor c_f from the approximation in
  ! Colebrook's 1939 ICE paper.  Re is the Reynolds number based on the
  ! hydraulic diameter, rr37 is the relative roughness divided by 3.7.
  ! It is useful to divide by 3.7 outside the runtime loops because it
  ! saves a floating point division at every timestep.

  implicit none
  integer, parameter :: dp=kind(0.d0)
  ! Relative roughness (-) and Reynolds number (-)
  real(dp), intent(in) :: rr37, Re
  real(dp) :: Colebrook

  Colebrook = 0.0625_dp / log10(rr37 + 7_dp/Re**0.9_dp )**2
end function Colebrook


function fricfac(d_h, roughness, rr, rr37, veloc, fric_app_num)
  ! Take a hydraulic diameter, roughness height, two views of relative
  ! roughness, air velocity and an integer telling which approximation
  ! to use.  Figure out the Fanning friction factor to use and return it.
  !
  !     Parameters:
  !       d_h             float          Hydraulic diameter (m)
  !       roughness       float          If +ve, roughness height (m).
  !                                      If -ve, Fanning friction factor (-)
  !       rr              float          Relative roughness (roughness / D_h)
  !                                      Not used if roughness is negative.
  !       rr37            float          Relative roughness divided by 3.7.
  !                                      Not used if roughness is negative.
  !       veloc           float          Air velocity (m/s)
  !       fric_app_num    int            Integer that maps to which equation
  !                                      to use for friction factor.  See
  !                                      below.
  !   Returns:
  !       fricfac         float          The Fanning friction factor (-)

  implicit none
  integer, parameter :: dp=kind(0.d0)

  real(dp), intent(in) :: d_h, roughness, rr, rr37, veloc

  ! Friction approximations:
  !     1     = Iterated Colebrook-White function
  !     2     = Colebrook's 1939 approximation (the default)
  !     3     = Moody's 1947 approximation
  !     4     = SES's 1974 approximation
  !     other = Prints a sarky message and stops.
  integer (kind=8), intent(in) :: fric_app_num

  ! Define the type of variable this function returns.  This is Fanning friction
  ! factor c_f, which is one-quarter of the Darcy friction factor lambda.
  real(dp) :: fricfac

  ! Define intermediate variables.
  real(dp) :: Colebrook, Re, Fanning_old
  integer (kind=8) :: count

  if (roughness < 0.0_dp) then
    ! The user set a negative roughness, meaning they wanted a constant
    ! friction factor.  Note that if they set a Darcy or Atkinson friction
    ! factor in the input file, we converted it to Fanning friction factor
    ! c_f well before we got here.
    fricfac = -roughness
  else
    ! Calculate the friction factor from the roughness height.

    ! First figure out the Reynolds number.  We assume a constant
    ! kinematic viscosity for air of 1.5E-5 m^2/s and ensure that
    ! Re is always a positive number.
    Re = abs(veloc) * d_h / 0.000015_dp

    ! Set the friction factor based on the Reynolds number.  Do the
    ! cases of high Reynolds number first, they're the most likely.
    ! Then the case of stationary air (the next most likely) and
    ! finally the laminar flow region and critical zone (lumped together).
    if (Re >= 2300._dp) then
      ! It's in the transition zone or the fully turbulent zone on the
      ! Moody chart.
      select case (fric_app_num)
        case (1)
          ! The user wants to iterate the Colebrook-White function.
          ! Start from Colebrook's approximation, it's the best guess.
          Fanning_old = Colebrook(rr37, Re)
          do count = 1, 50
            fricfac = 0.0625_dp / log10(rr37                            &
                                 + 1.255_dp/(Re * sqrt(Fanning_old)))**2

            ! Uncomment this write statement to spam your terminal with
            ! information as the iteration converges.  This may be useful
            ! if you suspect that 50 iterations are too few.
            ! write(*,'(A,I3,2(1X,F10.7))') "C-W", count, Fanning_old, fricfac

            ! Check if this re-assessment changed the result by less
            ! than 0.1%.  If it did, break.
            if (abs(fricfac - Fanning_old)/ Fanning_old < 0.001_dp) then
                ! It's converged, break out of the do loop.
                exit
            else
                ! Store this value for the next iteration.
                Fanning_old = fricfac
            end if
          end do
        case (2)
          ! Use the approximation in Colebrook's 1939 ICE paper.
          fricfac = Colebrook(rr37, Re)
        case (3)
          ! Use the approximation in Moody's 1947 ASME paper.
          fricfac = 0.001375_dp * (1_dp +                               &
                              (20000_dp * rr + 1E6_dp / Re)**0.333333_dp)
        case (4)
          ! Use the approximation in SES, a modification of Moody's
          ! to improve it at high roughness.  Note that 1431083.5
          ! is 16000 * 0.05^(-1.5).  Using it cuts out a division
          ! and introduces an error of 0.4 parts per billion in that
          ! term (I can live with that).
          fricfac = 0.001375_dp * (1_dp + (rr *                         &
           (19000_dp + 1431083.5_dp * rr**1.5_dp) + 1E6_dp / Re)**0.333333_dp)
        case default
          ! A new approximation has been used.  Whoever added it must
          ! have already dealt with a similar error messages printed in
          ! ProcessCalc in Hobyah.py.  Complain and stop.
          write(*,'(3(A,/),A)')                                         &
                  'A new type of friction factor has been added',       &
                  "but the code to handle it hasn't been added to",     &
                  'Fortran function fricfac in compressible.f95.',      &
                  'Please complain to whoever added it.'
          stop
      end select
    else if (Re < 0.1_dp) then
      ! It's practically stationary.  Use a fixed figure of c_f = 160.
      fricfac = 160.0_dp
    else
      ! It's laminar flow or in the critical zone.  Treat it as
      ! laminar flow.  We don't bother doing anything fancy to
      ! handle the critical zone (the transition from laminar flow
      ! to turbulent flow) because even in a very small tunnel vent
      ! duct (say 1 m diameter) the air velocity to get beyond the
      ! the critical zone is 2300 * 1.5E-5 / 1 = 0.035 m/s.  So,
      ! too low to be worried about.
      fricfac = 16.0_dp/Re
    end if
  end if
end function fricfac


function extrapolate(x_mid, count, x_vals, y_vals)
  ! Do linear interpolation and extrapolation (with two arrays of X and Y)
  ! to a Y-value that matches an X-value.  This routine was written to
  ! get duty points on fan flow-pressure characteristics, so extrapolation
  ! is allowed.  We assume that the two arrays are the same length and
  ! that the X values increase from low index to high index.  If those
  ! assumptions are not correct then horrible things may happen.
  ! We also assume that the X values are not equally spaced.
  !
  !   Parameters:
  !       x_mid       float       X-value we want Y for
  !       count       int         Count of the entries in x_vals and y_vals
  !       x_vals      (float)     Values on the X-axis
  !       y_vals      (float)     Values on the Y-axis
  !
  !   Returns:
  !    extrapolate    float       The interpolated (or extrapolated) Y value.

  implicit none
  integer, parameter :: dp=kind(0.d0)
  integer (kind=8), intent(in) :: count
  real(kind=dp), dimension(count), intent(in) :: x_vals, y_vals
  real(dp), intent(in) :: x_mid
  real(dp) :: extrapolate ! The Y-value corresponding to x_mid.

  integer (kind=8) :: cminus1, ii
  real(dp):: x1, x2, y1, y2

  cminus1 = count - 1
  x1 = x_vals(cminus1)

  ! First check if we are near or past the upper end of the data.
  if (x_mid .ge. x1) then
    ! Extrapolate forward from the last two points or interpolate
    ! between the last two points.  No need to set x1, we set it
    ! already above.
    y1 = y_vals(cminus1)
    x2 = x_vals(count)
    y2 = y_vals(count)
  else
    ! x_mid is below x_vals(count - 1).  Find the pair of
    ! values that x_mid lies between.
    do ii=2, cminus1
      if (x_mid .le. x_vals(ii)) then
        exit
      end if
    end do
    ! The counter ii now contains the index of the X value that is
    ! above x_mid.  This works when x_mid is in the middle of the
    ! range covered by the data and when x_mid is below the value
    ! in x_vals(1) too.
    cminus1 = ii - 1
    x1 = x_vals(cminus1)
    x2 = x_vals(ii)
    y1 = y_vals(cminus1)
    y2 = y_vals(ii)
  end if

  ! Check if y1 = y2 and take a shortcut if they do.
  if (y1 .eq. y2) then
    extrapolate = y1
  else
    extrapolate = y1 + (y2 - y1) / (x2 - x1) * (x_mid - x1)
  end if
end function extrapolate


subroutine baseback1(dtdx, c_M, u_M, c_R, u_R, c_N, u_N, c_b, u_b)
  ! Take (known) conditions at each end of a cell at the current timestep
  ! (c_M, u_M, c_R, u_R) and (estimated) conditions at the end of a
  ! backwards characteristic at the next timestep (c_N, u_N).
  ! Figure out where the characteristic intersects conditions at the
  ! current timestep and get interpolated values for the conditions at the
  ! base of the characteristic (c_b, u_b) using first-order interpolation.
  !
  !         dtdx            float           Timestep divided by cell length
  !         c_M             float           Celerity at the middle gridpoint
  !                                         in the current timestep.
  !         u_M             float           Velocity at the middle gridpoint
  !                                         in the current timestep.
  !         c_R             float           Celerity at the right gridpoint
  !                                         in the current timestep.
  !         u_R             float           Velocity at the right gridpoint
  !                                         in the current timestep.
  !         c_N             float           Celerity at the middle gridpoint
  !                                         in the next timestep.
  !         u_N             float           Velocity at the middle gridpoint
  !                                         in the next timestep.
  !
  !     Returns:
  !         c_b             float           Celerity at the base of the back
  !                                         characteristic at the current
  !                                         timestep.
  !         u_b             float           Velocity at the base of the back
  !                                         characteristic at the current
  !                                         timestep.
  !
  ! When calling this from Python you can use
  !   import compressible as ftn
  !   (c_b, u_b) = ftn.baseback1(dtdx, c_M, u_M, c_LR, u_LR, c_N, u_N)

  implicit none
  integer, parameter :: dp=kind(0.d0)

  real(dp), intent(in) :: dtdx, c_M, u_M, c_R, u_R, c_N, u_N

  ! Conditions at the base of the backwards characteristic.  These are
  ! calculated and returned.
  real(dp), intent(out) :: c_b, u_b

  ! Fraction of the grid spacing (0 to 1, we hope).
  real(dp) :: fraction

  ! Backwards characteristics have a steep slope.
  fraction = dtdx * (c_N - u_N)

  c_b = c_M + fraction * (c_R - c_M)
  u_b = u_M + fraction * (u_R - u_M)
  return
end subroutine baseback1


subroutine Basefwd1(dtdx, c_M, u_M, c_L, u_L, c_N, u_N, c_f, u_f)
  ! Take (known) conditions at each end of a cell at the current timestep
  ! (c_M, u_M, c_L, u_L) and (estimated) conditions at the end of a
  ! forwards characteristic at the next timestep (c_N, u_N).
  ! Figure out where the characteristic intersects conditions at the
  ! current timestep and get interpolated values for the conditions at the
  ! base of the characteristic (c_f, u_f) using first-order interpolation.
  !
  !         dtdx            float           Timestep divided by cell length
  !         c_M             float           Celerity at the middle gridpoint
  !                                         in the current timestep.
  !         u_M             float           Velocity at the middle gridpoint
  !                                         in the current timestep.
  !         c_L             float           Celerity at the left gridpoint
  !                                         in the current timestep.
  !         u_L             float           Velocity at the left gridpoint
  !                                         in the current timestep.
  !         c_N             float           Celerity at the middle gridpoint
  !                                         in the next timestep.
  !         u_N             float           Velocity at the middle gridpoint
  !                                         in the next timestep.
  !
  !     Returns:
  !         c_f             float           Celerity at the base of the forward
  !                                         characteristic at the current
  !                                         timestep.
  !         u_f             float           Velocity at the base of the forward
  !                                         characteristic at the current
  !                                         timestep.

  implicit none
  integer, parameter :: dp=kind(0.d0)

  real(dp), intent(in) :: dtdx, c_M, u_M, c_L, u_L, c_N, u_N

  ! Conditions at the base of the forwards characteristic.  These are
  ! calculated and returned.
  real(dp), intent(out) :: c_f, u_f

  ! Fraction of the grid spacing (0 to 1, we hope).
  real(dp) :: fraction

  ! Forwards characteristics have a shallow slope.
  fraction = dtdx * (c_N + u_N)

  c_f = c_M + fraction * (c_L - c_M)
  u_f = u_M + fraction * (u_L - u_M)
  return
end subroutine Basefwd1


subroutine fixedvel(u_N, back_end, dtdx, d_h, roughness, rr, rr37,      &
                    fric_const, max_iter, fric_app_num, converge, psi,  &
                    JFTRdrag, c_array, u_array, gridpoints, cells,      &
                    c_N, converged)
  ! Process the gridpoint at one end of a segment that connects to
  ! outside atmosphere.  There is a constant air velocity inside the
  ! portal and a celerity is calculated that maintains that air speed.
  !
  !   Parameters:
  !       u_N             float           Fixed air velocity to set at the
  !                                       portal.
  !       back_end        bool            True if this is a back end.  False
  !                                       if it is not.  Used to select which
  !                                       characteristic to use.
  !       dtdx            float           A constant in the characteristics
  !                                       calculation, dt/dx_local
  !       d_h             float           Hydraulic diameter of the segment
  !       roughness       float           If +ve, the roughness height of
  !                                       the segment.  If -ve, the fixed
  !                                       Fanning friction factor (-c_f).
  !       rr              float           Relative roughness (roughness / D_h)
  !                                       Not used if roughness is negative.
  !       rr37            float           Relative roughness divided by 3.7.
  !                                       Not used if roughness is negative.
  !       fric_const      float           A constant in the friction calc,
  !                                       0.5 * perimeter / area * dt
  !       max_iter        int             A counter of the iterations.
  !       fric_app_num    int             Integer setting which friction
  !                                       factor approximation to use.
  !       converge        float           A value to decide when the
  !                                       calculation is converged.  If
  !                                       a celerity from the current
  !                                       iteration differs from the
  !                                       celerity at the previous
  !                                       iteration, the iterating stops.
  !       psi             float           An exponent in the isentropic
  !                                       flow calculation.
  !       JFTRdrag        float           The traffic drag and jet fan
  !                                       thrust term in the cell next
  !                                       next to the portal.  It is
  !                                       expressed as m**2/s**2 per
  !                                       metre over the length of the
  !                                       cell.
  !       c_array         (gridpoints)    List of all the celerities at
  !                                       gridpoints in one segment.
  !       u_array         (gridpoints)    List of all the velocities at
  !                                       gridpoints in one segment.
  !       gridpoints      int             The size of c_array and u_array.
  !       cells           int             gridpoints - 1.
  !
  !   Returns:
  !       c_N             float           Celerity at the gridpoint just
  !                                       inside the portal that is
  !                                       appropriate for velocity u_N.
  !       converged        Bool           True if the calculation converged,
  !                                       False if it did not.

  implicit none
  integer, parameter :: dp=kind(0.d0)

  ! Define all the arguments to the function.
  real(dp), intent(in) :: u_N, dtdx, d_h, roughness, rr, rr37, fric_const,  &
                          converge, psi, JFTRdrag

  integer (kind=8), intent(in) :: fric_app_num, max_iter, gridpoints, cells
  logical, intent(in) :: back_end
  real(dp), dimension(gridpoints), intent(in) :: c_array, u_array

  ! We return two values, the celerity needed at the portal and Boolean
  ! value that is .True. if the calculation converged and .False. if it
  ! did not.
  !
  real(dp), intent(out) :: c_N
  logical, intent(out) :: converged

  ! Define variables we use in the calculation.
  integer (kind=8) :: count
  real(dp) :: c_M, c_LR, u_M, u_LR, c_bf, u_bf, c_N_old, Fanning,       &
              E_bfdt, fricfac

  if (back_end) then
    ! Get the conditions at the first and second gridpoints.
    c_M = c_array(1)
    c_LR = c_array(2)
    u_M = u_array(1)
    u_LR = u_array(2)
  else
    ! Get the conditions at the last two gridpoints.
    c_M = c_array(gridpoints)
    c_LR = c_array(cells)
    u_M = u_array(gridpoints)
    u_LR = u_array(cells)
  end if

  ! Assume that we succeed.  This will be set False if the do loop below
  ! runs out its count of iterations before converging.
  converged = .True.

  ! Now iterate to get a new value of c_N.  Our first guess is that it
  ! is equal to c_M.
  c_N = c_M
  do count = 1, max_iter
    c_N_old = c_N

    ! Get the conditions at the base of the characteristic.  If this is
    ! the gridpoint at the back end it is a backwards characteristic.
    ! If this is the gridpoint at the forward end it is a forwards
    ! characteristic.
    if (back_end) then
      call baseback1(dtdx, c_M, u_M, c_LR, u_LR, c_N, u_N, c_bf, u_bf)

      ! Calculate the Fanning friction factor, based on the
      ! current value of u_bf.
      Fanning = fricfac(d_h, roughness, rr, rr37, u_bf, fric_app_num)

      ! Get the friction loss term, the traffic term and the jet fan term.
      E_bfdt = fric_const * Fanning * u_bf * abs(u_bf) + JFTRdrag

      ! Get a new value of c_N from the backwards characteristic equation,
      ! assuming a fixed value of u_N.
      c_N = c_bf + (u_N - u_bf + E_bfdt)/psi
    else
      ! It's at the forward end.
      call basefwd1(dtdx, c_M, u_M, c_LR, u_LR, c_N, u_N, c_bf, u_bf)
      Fanning = fricfac(d_h, roughness, rr, rr37, u_bf, fric_app_num)
      E_bfdt = fric_const * Fanning * u_bf * abs(u_bf) + JFTRdrag

      ! Get a new value of c_N from the forwards characteristic equation.
      c_N = c_bf + (u_bf - u_N - E_bfdt)/psi
    end if
    if (abs(c_N - c_N_old) <= converge) then
      ! Break out of the loop.
      exit
    else if (count .eq. max_iter) then
      ! This is the last iteration in the loop and it didn't converge.
      converged = .False.
    end if
  end do
  ! When we get to here, the calculation converged or the counter of
  ! iterations timed out.
  return
end subroutine fixedvel


subroutine openend(c_outside, zeta_in, zeta_out, back_end, dtdx, d_h,   &
            roughness, rr, rr37, fric_const, max_iter, fric_app_num,    &
            converge, psi, JFTRdrag, c_array, u_array, gridpoints,      &
            c_N, u_N, converged)
  ! Process the cell at one end of a segment that connects to outside
  ! atmosphere.  The air outside the portal has a given pressure (expressed
  ! as a celerity), the gridpoint just inside the portal has conditions at
  ! the previous timestep, and there are conditions at the previous timestep
  ! at the other end of the cell.
  !
  ! Calculate new values of celerity and velocity at the gridpoint just
  ! inside the portal.
  !
  !   Parameters:
  !       c_outside       float           Celerity of air outside the portal.
  !       zeta_in         float           Pressure loss factor for inflow.
  !       zeta_out        float           Pressure loss factor for outflow.
  !       back_end        bool            True if this is a back end.  False
  !                                       if it is not.  Used to select which
  !                                       characteristic to use.
  !       dtdx            float           A constant in the characteristics
  !                                       calculation, dt/dx_local
  !       d_h             float           Hydraulic diameter of the segment
  !       roughness       float           If +ve, the roughness height of
  !                                       the segment.  If -ve, the fixed
  !                                       Fanning friction factor (-c_f).
  !       rr              float           Relative roughness (roughness / D_h)
  !                                       Not used if roughness is negative.
  !       rr37            float           Relative roughness divided by 3.7.
  !                                       Not used if roughness is negative.
  !       fric_const      float           A constant in the friction calc,
  !                                       0.5 * perimeter / area * dt
  !       max_iter        int             A counter of the iterations.
  !       fric_app_num    int             Integer setting which friction
  !                                       factor approximation to use.
  !       converge        float           A value to decide when the
  !                                       calculation is converged.  If
  !                                       a celerity from the current
  !                                       iteration differs from the
  !                                       celerity at the previous
  !                                       iteration, the iterating stops.
  !       psi             float           An exponent in the isentropic
  !                                       flow calculation.
  !       JFTRdrag        float           The traffic drag and jet fan
  !                                       thrust term in the cell next
  !                                       next to the portal.  It is
  !                                       expressed as m**2/s**2 per
  !                                       metre over the length of the
  !                                       cell.
  !       c_array         (gridpoints)    List of all the celerities at
  !                                       gridpoints in one segment.
  !       u_array         (gridpoints)    List of all the velocities at
  !                                       gridpoints in one segment.
  !
  !   Returns:
  !       c_N             float           Celerity at the gridpoint just
  !                                       inside the portal in the next
  !                                       timestep.
  !       u_N             float           Velocity at the gridpoint just
  !                                       inside the portal in the next
  !                                       timestep.
  !       converged         Bool          True if the calculation converged,
  !                                       False if it did not.

  implicit none
  integer, parameter :: dp=kind(0.d0)
  ! Define all the arguments to the function.
  real(dp), intent(in) :: c_outside, zeta_in, zeta_out, dtdx, d_h,      &
                          roughness, rr, rr37, fric_const, converge,    &
                          psi, JFTRdrag
  integer (kind=8), intent(in) :: fric_app_num, max_iter, gridpoints

  logical, intent(in) :: back_end
  real(dp), dimension(gridpoints), intent(in) :: c_array, u_array

  ! We return three values, the celerity and velocity at the portal and
  ! a success/failure Boolean'
  real(dp), intent(out) :: c_N, u_N
  logical, intent(out) :: converged


  ! Define variables we use in the calculation.
  integer (kind=8) :: count, previous
  real(dp) :: c_M, c_LR, u_M, u_LR, c_bf, u_bf, c_N_old, Fanning,       &
              E_bfdt, fricfac

  if (back_end) then
    ! Get the conditions at the first and second gridpoints.
    c_M = c_array(1)
    c_LR = c_array(2)
    u_M = u_array(1)
    u_LR = u_array(2)
  else
    ! Get the conditions at the last two gridpoints.
    previous = gridpoints-1
    c_M = c_array(gridpoints)
    c_LR = c_array(previous)
    u_M = u_array(gridpoints)
    u_LR = u_array(previous)
  end if

  ! Assume that we succeed.  This will be set False if the do loop below
  ! times out instead of converging.
  converged = .True.

  ! Now iterate to get new values of c_N and u_N.  Our first guess is that
  ! they are equal to c_M and u_M.
  c_N = c_M
  u_N = u_M
  do count = 1, max_iter
    c_N_old = c_N

    ! Get the conditions at the base of the characteristic.  If this is
    ! the gridpoint at the back end it is a backwards characteristic.
    ! If this is the gridpoint at the forward end it is a forwards
    ! characteristic.
    if (back_end) then
      call baseback1(dtdx, c_M, u_M, c_LR, u_LR, c_N, u_N, c_bf, u_bf)

      ! Calculate the Fanning friction factor, based on the
      ! current value of u_bf.
      Fanning = fricfac(d_h, roughness, rr, rr37, u_bf, fric_app_num)

      ! Get the loss term.
      E_bfdt = fric_const * Fanning * u_bf * abs(u_bf) + JFTRdrag

      ! Get the velocity and celerity for this estimate
      u_N = u_bf + psi * (c_N - c_bf) - E_bfdt
      call portalcelerity(c_outside, u_N, zeta_in, zeta_out, psi, c_N)
    else
      call basefwd1(dtdx, c_M, u_M, c_LR, u_LR, c_N, u_N, c_bf, u_bf)
      Fanning = fricfac(d_h, roughness, rr, rr37, u_bf, fric_app_num)
      E_bfdt = fric_const * Fanning * u_bf * abs(u_bf) + JFTRdrag
      u_N = u_bf - psi * (c_N - c_bf) - E_bfdt
      call portalcelerity(c_outside, -u_N, zeta_in, zeta_out, psi, c_N)
    end if

    if (abs(c_N - c_N_old) <= converge) then
      ! Break out of the loop.
      exit
    else if (count .eq. max_iter) then
      ! This is the last iteration in the loop and it didn't converge.
      converged = .False.
    end if
  end do
  ! When we get to here, the calculation converged or the counter of
  ! iterations timed out.
  return
end subroutine openend


subroutine portalcelerity(c_outside, u_inside, zeta_in, zeta_out, psi, c_inside)
    ! Take the celerity of air outside a portal, the air velocity inside
    ! the portal, details of the connection at the portal (k-factors) and
    ! the constant psi.  Calculate the celerity inside the portal that
    ! represents the local static pressure.
    ! The calculation is a simplified version of equation 5 in:
    !  Fox, J A and Higton, N N, ``Pressure transient predictions in railway
    !  tunnel complexes'', Proceedings of the 3rd International Symposium on
    !  the Aerodynamics and Ventilation of Vehicle Tunnels (ISAVVT), BHRA, 1979.
    !
    !   Parameters:
    !       c_outside       float           Celerity of stationary air outside
    !                                       the portal (m/s).  This may include
    !                                       a component of wind pressure or
    !                                       stack pressure.
    !       u_inside        float           Air velocity inside the portal
    !                                       (m/s).
    !       zeta_in         float           Pressure loss factor (k-factor)
    !                                       for inflow.  Applied to u_inside.
    !       zeta_out        float           Pressure loss factor (k-factor)
    !                                       for outflow.  Applied to u_inside.
    !       psi             float           An exponent in the isentropic
    !                                       flow calculation.
    !
    !   Returns:
    !       c_inside        float           Celerity of air inside the
    !                                       portal (m/s), after applying the
    !                                       pressure losses and converting
    !                                       some total pressure to dynamic
    !                                       pressure.  c_inside is the
    !                                       equivalent of static pressure,
    !                                       not total pressure.
  implicit none
  integer, parameter :: dp=kind(0.d0)
  ! Define the values being passed.  There are no intermediate variables.
  real(dp), intent(in) :: c_outside, u_inside, zeta_in, zeta_out, psi
  real(dp), intent(out) :: c_inside

  if (u_inside > 0.0_dp) then
    ! We have inflow from atmosphere to the portal.
    ! We add a factor of 1 to zeta to represent the conversion of
    ! part of the total pressure into dynamic pressure.  The value
    ! of c thus represents the static pressure inside the portal.
    c_inside = sqrt(c_outside**2 - (zeta_in + 1_dp)/psi * u_inside**2)
  else if (abs(zeta_out - 1.0_dp) < 0.000000001_dp) then
    ! We have outflow and we are losing exactly one velocity head,
    ! so we can use a shortcut.  The static pressure inside the
    ! tunnel equals the total pressure outside (for what it's worth,
    ! it also equals the static pressure outside).
    ! Note that the test above replicates Python's math.isclose() function.
    c_inside = c_outside
  else
    ! We have outflow but we are not losing exactly one velocity
    ! head. We have to do the full calculation.
    ! We subtract a factor of 1 from zeta_out to represent the
    ! dissipation of one dynamic head outside the portal.  If
    ! the user set zeta_out to be less than one we get some static
    ! regain, as if we had a diffuser at the outflow portal.
    c_inside = sqrt(c_outside**2 + (zeta_out - 1_dp)/psi * u_inside**2)
  end if
  return
end subroutine portalcelerity


subroutine celvel1(c_array, u_array, d_h, roughness, rr, rr37,          &
                   zeta_back_bf, zeta_back_fb, zeta_fwd_bf, zeta_fwd_fb,&
                   back_type, back_value,  fwd_type, fwd_value,         &
                   fric_const, dtdx, converge, max_iter, fric_app_num,  &
                   last_time, psi, vel_frac, JFTR_drag, gridpoints,     &
                   cells, c_new, u_new, message)

  ! Take arrays of celerity and velocity values at gridpoints in one segment
  ! in the previous timestep along with the arrays of traffic drag and jet
  ! fan thrust in the cells of one segment.  Calculate as many values of
  ! celerity and velocity at gridpoints in the segment in the next timestep
  ! as possible.  The only values this routine does not calculate are at
  ! boundary gridpoints (gridpoints that have other gridpoints right next
  ! to them - gridpoints at joins, fans, dampers etc.).  Boundary gridpoints
  ! must be solved in conjunction with values in other segments and
  ! in some cases (fans and dampers) have additional information to define
  ! the state of the entity at a particular time (e.g. fan speed, damper
  ! resistance).  Those are handled in specific routines after all the
  ! simpler gridpoints (which can be calculated by this routine) have
  ! been calculated.
  !
  ! Return a new array of celerity values, a new array of velocity values
  ! and a string stating that the calculation succeeded or stating what
  ! last failed in the calculation.

  implicit none
  integer, parameter :: dp=kind(0.d0)

  integer (kind=8), intent(in) :: gridpoints, cells, fric_app_num, max_iter

  real(dp), dimension(gridpoints), intent(in) :: c_array, u_array

  real(dp), dimension(cells), intent(in) :: JFTR_drag

  real(dp), intent(in) :: d_h, roughness, rr, rr37,                     &
                          zeta_back_bf, zeta_back_fb,                   &
                          zeta_fwd_bf, zeta_fwd_fb,                     &
                          back_value, fwd_value,                        &
                          fric_const, dtdx, converge, last_time,        &
                          psi, vel_frac

  character (len = 1), intent(in) :: back_type, fwd_type


  ! Define the outputs.  These are arrays of celerity and velocity at
  ! the next timestep and a string with a success or failure message.
  real(dp), dimension(gridpoints), intent(out) :: c_new, u_new

  character (len = 53), intent(out) :: message
  ! The message could be one of the following:
  !   "The solution converged.                              "
  !   "> OpenEnd calc didn't converge at the back end       "
  !   "> OpenEnd calc didn't converge at the forward end    "
  !   "> FixedVel calc didn't converge at the back end      "
  !   "> FixedVel calc didn't converge at the forward end   "
  !   "> CelVel1 calc didn't converge at interior gridpoints"
  ! Once it gets returned to Python it is decoded with "bytes.decode()".



  ! Define the intermediate variables.
  integer (kind=8) :: gr_index, prev_gp, next_gp, count
  real(dp) :: c_N, u_N,  c_N_old, c_N_alt
  real(dp) :: c_M, c_L, c_R, u_M, u_L, u_R, c_b, c_f, u_b, u_f
  real(dp) :: Fanning_b, Fanning_f, E_bdt, E_fdt, fricfac
  real(dp) :: left_TRdrag, right_TRdrag
  logical :: success

  ! Start by assuming that the solution doesn't fail.  Whichever
  ! solution failed last will be what gets reported: the sequence
  ! is: first cell (if at a daylight portal); last cell (if at a
  ! daylight portal); then an interior cell.  This can cause problems
  ! with troubleshooting.
  message = "The solution converged."

  do gr_index = 1, gridpoints
    if (gr_index == 1) then
      ! This is the gridpoint at the back end.  Check if it is
      ! a type that can be handled here (open to atmosphere or
      ! fixed conditions).
      if (back_type == 'p') then
        ! This is an open portal with a fixed air pressure
        ! outside it.  We call a routine to calculate with
        ! a fixed celerity outside, portal loss factors for
        ! inflow and outflow and a characteristic in one cell.
        call openend(back_value, zeta_back_bf, zeta_back_fb, .True.,    &
                     dtdx, d_h, roughness, rr, rr37, fric_const,        &
                     max_iter, fric_app_num, converge, psi,             &
                     JFTR_drag(1), c_array, u_array, gridpoints,        &
                     c_N, u_N, success)
        if (.not. success) then
          message = "> OpenEnd calc didn't converge at the back end"
        end if
      else if (back_type == 'v' .or. back_type == 'q') then
        ! We call a routine to calculate the celerity at the
        ! portal that give us a fixed air velocity.  We don't
        ! feed this the k-factors because we don't need them.
        u_N = back_value * vel_frac
        call fixedvel(u_N, .True., dtdx, d_h, roughness, rr, rr37,      &
                      fric_const, max_iter,                             &
                      fric_app_num, converge, psi, JFTR_drag(1),        &
                      c_array, u_array, gridpoints, cells, c_N, success)
        if (.not. success) then
          message = "> FixedVel calc didn't converge at the back end"
        end if
      else
        ! The gridpoint at this end of the segment end is handled
        ! in a routine that considers flow split at a junction or
        ! pressure changes at a fan or somesuch.  Put in values that
        ! will tank the calculation if we accidentally use these
        ! numbers at the next timestep.
        !
        c_N = 1e12_dp
        u_N = 42.0_dp
      end if
    else if (gr_index == gridpoints) then
      if (fwd_type == 'p') then
        call openend(fwd_value, zeta_fwd_fb, zeta_fwd_bf, .False.,      &
                     dtdx, d_h, roughness, rr, rr37, fric_const,        &
                     max_iter, fric_app_num, converge, psi,             &
                     JFTR_drag(cells), c_array, u_array,                &
                     gridpoints, c_N, u_N, success)
        if (.not. success) then
          message = "> OpenEnd calc didn't converge at the forward end"
        end if
      else if (fwd_type == 'v') then
        ! We call a routine to calculate the conditions at
        ! the portal that force a fixed air velocity.
        u_N = fwd_value * vel_frac
        call fixedvel(u_N, .False., dtdx, d_h, roughness, rr, rr37,     &
                      fric_const, max_iter,                             &
                      fric_app_num, converge, psi,                      &
                      JFTR_drag(cells), c_array, u_array,               &
                      gridpoints, cells, c_N, success)
        if (.not. success) then
          message = "> FixedVel calc didn't converge at the forward end"
        end if
      else
        c_N = 1e12_dp
        u_N = 42.0_dp
      end if
    else
      ! This is a gridpoint in the middle.  We have a backwards
      ! characteristic and a forwards characteristic.  Get the values
      ! at the current gridpoint and the gridpoints on each side.
      prev_gp = gr_index - 1
      next_gp  = gr_index + 1
      c_L = c_array(prev_gp)
      u_L = u_array(prev_gp)
      c_M = c_array(gr_index)
      u_M = u_array(gr_index)
      c_R = c_array(next_gp)
      u_R = u_array(next_gp)
      left_TRdrag = JFTR_drag(prev_gp)
      right_TRdrag = JFTR_drag(gr_index)
      ! Now iterate to get values of c_N and u_N.  Our first guess
      ! is that they are equal to c_M and u_M.
      c_N = c_M
      u_N = u_M

      do count = 1, max_iter
        ! Get the conditions at the base of the backwards and
        ! forwards characteristics.
        call baseback1(dtdx, c_M, u_M, c_R, u_R, c_N, u_N, c_b, u_b)
        call basefwd1(dtdx,  c_M, u_M, c_L, u_L, c_N, u_N, c_f, u_f)

        ! Calculate the Fanning friction factors and the loss
        ! terms.
        Fanning_b = fricfac(d_h, roughness, rr, rr37, u_b, fric_app_num)
        Fanning_f = fricfac(d_h, roughness, rr, rr37, u_f, fric_app_num)
        E_bdt = fric_const * Fanning_b * u_b * abs(u_b) + right_TRdrag
        E_fdt = fric_const * Fanning_f * u_f * abs(u_f) + left_TRdrag

        ! Get a new value of u_N from the two characteristic
        ! equations.
        u_N = 0.5_dp * (u_f + u_b + psi * (c_f - c_b) - E_bdt - E_fdt)

        ! Store the current value of c_N.
        c_N_old = c_N
        c_N = c_f + (u_f - u_N - E_fdt) / psi
        c_N_alt = c_f + (u_f - u_N - E_fdt) / psi
        if (c_N .ne. c_N_alt) then
          write(*,'(3(A,/), 2(A, F0.5,/), 5(A,/), (A, F0.5,A,/), 3(A,/))') &
              '> Fouled up when calculating with two character-', &
              '> istics, ended up with a gridpoint that had the', &
              '> following values:', &
              '>   celerity = ', c_N, &
              '>   velocity = ', u_N, &
              '> If either of these are "NaN" or there are runtime', &
              '> warnings printed to the screen, try increasing', &
              '> max_vel in the "settings" block to force larger', &
              '> cell sizes.  See also the Miscellany chapter in', &
              '> the User Manual for more details.', &
              '> Try setting the aero_time to ', last_time, ' seconds and', &
              '> plotting celerity and velocity values.  This', &
              '> will show the state of the system at the last', &
              '> stable timestep.'
            stop
        end if
        if (abs(c_N - c_N_old) <= converge) then
          ! Leave the do loop.
          exit
        else if (count .eq. max_iter) then
          ! This is the last iteration in this do loop and it didn't converge.
          ! Set the message that we return to the calling routine.
          message = "> CelVel1 calc didn't converge at interior gridpoints"
        end if
      end do
      ! Once we get to here we have either converged or run out the count
      ! of iterations.
    end if
    c_new(gr_index) = c_N
    u_new(gr_index) = u_N
  end do
  return
end subroutine celvel1


subroutine twowaymoc2a(varies, fixed, char1, char2, continuity, P_stag)
  ! Define four equations that need to be satisfied to calculate new
  ! values of celerity and velocity on each side of a two-way junction
  ! that may have different areas on the two sides.  These are:
  !  * two forward characteristics in the two cells,
  !  * one mass continuity equation at the node, and
  !  * the difference between stagnation pressures at both sides of
  !    the node.
  ! All four equations are expressed in a way that makes their desired
  ! result zero, so that scipy.optimize.fsolve can solve the system of
  ! equations by varying four values.
  !
  ! The function calculates a new value of friction factor during
  ! every iteration, which might be a bit over the top.  We'll wait
  ! and see how slow the whole thing is and what effect calculating
  ! c_f from u_M1 and u_M2 has later.

  implicit none
  integer, parameter :: dp=kind(0.d0)
  ! Define the values being passed in.
  real(dp), dimension(4), intent(in) :: varies
  real(dp), dimension(28), intent(in) :: fixed

  ! First define the four values that scipy.optimize.fsolve varies, these
  ! are passed in 'varies'.
  real(dp) :: c_N1, u_N1, c_N2, u_N2

  ! Next define the genuine constants, these are passed in 'fixed'.
  real(dp) :: psi, fric_const1, dtdx1, fric_const2, dtdx2,              &
              c_M1, u_M1, c_L1, u_L1, area1, d_h1, roughness1,          &
              rr1, rr371, stag_1, JFTRdrag1,                            &
              c_M2, u_M2, c_L2, u_L2, area2, d_h2, roughness2,          &
              rr2, rr372, stag_2, JFTRdrag2
  integer (kind=8) :: fric_app_num

  ! Identify the values returned by the routine.
  real (dp), intent(out) :: char1, char2, continuity, P_stag

  ! Define the intermediate variables.
  real(dp) :: c_f1, u_f1, Fanning_1, E_1dt, c_f2, u_f2, Fanning_2, E_2dt

  ! Define the types of values returned by Fortran functions.
  real(dp) :: fricfac

  ! Unpack all the values in arrays into suitably-named variables.
  c_N1 = varies(1)
  u_N1 = varies(2)
  c_N2 = varies(3)
  u_N2 = varies(4)

  psi = fixed(1)
  fric_app_num = int(fixed(2))
  dtdx1 = fixed(3)
  area1 = fixed(4)
  d_h1 = fixed(5)
  rr1 =  fixed(6)
  rr371 =  fixed(7)
  fric_const1 = fixed(8)
  roughness1 = fixed(9)
  stag_1 = fixed(10)
  JFTRdrag1 = fixed(11)
  c_M1 = fixed(12)
  u_M1 = fixed(13)
  c_L1 = fixed(14)
  u_L1 = fixed(15)
  dtdx2 = fixed(16)
  area2 = fixed(17)
  d_h2 = fixed(18)
  rr2 =  fixed(19)
  rr372 =  fixed(20)
  fric_const2 = fixed(21)
  roughness2 = fixed(22)
  stag_2 = fixed(23)
  JFTRdrag2 = fixed(24)
  c_M2 = fixed(25)
  u_M2 = fixed(26)
  c_L2 = fixed(27)
  u_L2 = fixed(28)

  ! Get the conditions at the base of the forwards characteristic
  ! in the first cell.
  call basefwd1(dtdx1, c_M1, u_M1, c_L1, u_L1, c_N1, u_N1, c_f1, u_f1)
  ! Get the conditions at the base of the forwards characteristic
  ! in the second cell.
  call basefwd1(dtdx2, c_M2, u_M2, c_L2, u_L2, c_N2, u_N2, c_f2, u_f2)

  ! Calculate the Fanning friction factors for these velocities.
  Fanning_1 = fricfac(d_h1, roughness1, rr1, rr371, u_f1, fric_app_num)
  Fanning_2 = fricfac(d_h2, roughness2, rr2, rr372, u_f2, fric_app_num)

  ! Get new values of the friction terms.
  E_1dt = fric_const1 * Fanning_1 * u_f1 * abs(u_f1) + JFTRdrag1
  E_2dt = fric_const2 * Fanning_2 * u_f2 * abs(u_f2) + JFTRdrag2

  ! Define functions for the two forwards characteristics.  These both
  ! should equal zero.
  char1 = psi * (c_N1 - c_f1) + (u_N1 - u_f1) + E_1dt
  char2 = psi * (c_N2 - c_f2) + (u_N2 - u_f2) + E_2dt

  ! Define the continuity equation for compressible flow.  The way
  ! the signs of the velocities are set up means that this should
  ! also equal zero.
  continuity = area1 * u_N1 * (c_N1/c_N2)**psi + area2 * u_N2

  ! Define an equation giving the difference between the stagnation
  ! pressure at N1 and the stagnation pressure at N2.  This should
  ! be zero.
  P_stag = c_N1**2 + stag_1 * u_N1**2 - c_N2**2 - stag_2 * u_N2**2

  return
end subroutine twowaymoc2a


subroutine threewaymoc2a(varies, fixed, char1, char2, char3,            &
                         continuity, P_stag1, P_stag2)
  ! Define six equations that need to be satisfied to calculate new
  ! values of celerity and velocity at points in three cells at a
  ! three-way junction.  These are:
  !  * three forward characteristics in the three cells,
  !  * one mass continuity equation at the node, and
  !  * two calculations of differences between stagnation pressure
  !    at the node.
  ! All six equations are expressed in a way that makes their desired
  ! result zero, so that scipy.optimize.fsolve can solve the system of
  ! equations.

  implicit none
  integer, parameter :: dp=kind(0.d0)
  ! Define the values being passed in.
  real(dp), dimension(6), intent(in) :: varies
  real(dp), dimension(41), intent(in) :: fixed

  ! First define the six values that scipy.optimize.fsolve varies, these
  ! are passed in 'varies'.
  real(dp) :: c_N1, u_N1, c_N2, u_N2, c_N3, u_N3

  ! Next define the genuine constants, these are passed in 'fixed'.
  real(dp) :: psi, fric_const1, dtdx1, fric_const2, dtdx2,              &
                   fric_const3, dtdx3,                                  &
              c_M1, u_M1, c_L1, u_L1, area1, d_h1, roughness1,          &
              rr1, rr371, stag_1, JFTRdrag1,                            &
              c_M2, u_M2, c_L2, u_L2, area2, d_h2, roughness2,          &
              rr2, rr372, stag_2, JFTRdrag2,                            &
              c_M3, u_M3, c_L3, u_L3, area3, d_h3, roughness3,          &
              rr3, rr373, stag_3, JFTRdrag3
  integer (kind=8) :: fric_app_num

  ! Identify the values returned by the routine.
  real (dp), intent(out) :: char1, char2, char3, continuity, P_stag1, P_stag2

  ! Define the intermediate variables.
  real(dp) :: c_f1, u_f1, Fanning_1, E_1dt, stag1_term,                 &
              c_f2, u_f2, Fanning_2, E_2dt,                             &
              c_f3, u_f3, Fanning_3, E_3dt

  ! Define the types of values returned by Fortran functions.
  real(dp) :: fricfac

  ! Unpack all the values in arrays into suitably-named variables.
  c_N1 = varies(1)
  u_N1 = varies(2)
  c_N2 = varies(3)
  u_N2 = varies(4)
  c_N3 = varies(5)
  u_N3 = varies(6)

  psi = fixed(1)
  fric_app_num = int(fixed(2))
  dtdx1 = fixed(3)
  area1 = fixed(4)
  d_h1 = fixed(5)
  rr1 =  fixed(6)
  rr371 =  fixed(7)
  fric_const1 = fixed(8)
  roughness1 = fixed(9)
  stag_1 = fixed(10)
  JFTRdrag1 = fixed(11)
  c_M1 = fixed(12)
  u_M1 = fixed(13)
  c_L1 = fixed(14)
  u_L1 = fixed(15)
  dtdx2 = fixed(16)
  area2 = fixed(17)
  d_h2 = fixed(18)
  rr2 =  fixed(19)
  rr372 =  fixed(20)
  fric_const2 = fixed(21)
  roughness2 = fixed(22)
  stag_2 = fixed(23)
  JFTRdrag2 = fixed(24)
  c_M2 = fixed(25)
  u_M2 = fixed(26)
  c_L2 = fixed(27)
  u_L2 = fixed(28)
  dtdx3 = fixed(29)
  area3 = fixed(30)
  d_h3 = fixed(31)
  rr3 =  fixed(32)
  rr373 =  fixed(33)
  fric_const3 = fixed(34)
  roughness3 = fixed(35)
  stag_3 = fixed(36)
  JFTRdrag3 = fixed(37)
  c_M3 = fixed(38)
  u_M3 = fixed(39)
  c_L3 = fixed(40)
  u_L3 = fixed(41)

  ! Get the conditions at the base of the forwards characteristics
  call basefwd1(dtdx1, c_M1, u_M1, c_L1, u_L1, c_N1, u_N1, c_f1, u_f1)
  call basefwd1(dtdx2, c_M2, u_M2, c_L2, u_L2, c_N2, u_N2, c_f2, u_f2)
  call basefwd1(dtdx3, c_M3, u_M3, c_L3, u_L3, c_N3, u_N3, c_f3, u_f3)

  ! Calculate the Fanning friction factors for these velocities.
  Fanning_1 = fricfac(d_h1, roughness1, rr1, rr371, u_f1, fric_app_num)
  Fanning_2 = fricfac(d_h2, roughness2, rr2, rr372, u_f2, fric_app_num)
  Fanning_3 = fricfac(d_h3, roughness3, rr3, rr373, u_f3, fric_app_num)

  ! Get new values of the friction, jet fan and traffic terms.
  E_1dt = fric_const1 * Fanning_1 * u_f1 * abs(u_f1) + JFTRdrag1
  E_2dt = fric_const2 * Fanning_2 * u_f2 * abs(u_f2) + JFTRdrag2
  E_3dt = fric_const3 * Fanning_3 * u_f3 * abs(u_f3) + JFTRdrag3

  ! Define functions for the three characteristics.  These all
  ! should equal zero.
  char1 = psi * (c_N1 - c_f1) + (u_N1 - u_f1) + E_1dt
  char2 = psi * (c_N2 - c_f2) + (u_N2 - u_f2) + E_2dt
  char3 = psi * (c_N3 - c_f3) + (u_N3 - u_f3) + E_3dt

  ! Define the continuity equation for compressible flow.  The way
  ! the signs of the velocities are set up means that this should
  ! also equal zero.
  continuity = area1 * u_N1 * (c_N1/c_N2)**psi + area2 * u_N2           &
             + area3 * u_N3 * (c_N3/c_N2)**psi

  ! There are terms in the stagnation pressure equations that we use
  ! in more than one equation.  Put them into one variable.
  stag1_term = c_N1**2 + stag_1 * u_N1**2

  ! Define two equations giving the difference between the stagnation
  ! pressures in two pairs of the gridpoints at the node.
  P_stag1 = stag1_term - c_N2**2 - stag_2*u_N2**2
  P_stag2 = stag1_term - c_N3**2 - stag_3*u_N3**2

  return
end subroutine threewaymoc2a


subroutine fourwaymoc2a(varies, fixed, char1, char2, char3, char4,     &
                        continuity, P_stag1, P_stag2, P_stag3)
  ! Define eight equations that need to be satisfied to calculate new
  ! values of celerity and velocity at points in four cells at a
  ! four-way junction.  These are:
  !  * four forward characteristics in the four cells,
  !  * one mass continuity equation at the node, and
  !  * three calculations of differences between stagnation pressure
  !    at the node.

  implicit none
  integer, parameter :: dp=kind(0.d0)
  ! Define the values being passed in.
  real(dp), dimension(8), intent(in) :: varies
  real(dp), dimension(54), intent(in) :: fixed

  ! First define the eight values that scipy.optimize.fsolve varies, these
  ! are passed in 'varies'.
  real(dp) :: c_N1, u_N1, c_N2, u_N2, c_N3, u_N3, c_N4, u_N4

  ! Next define the genuine constants, these are passed in 'fixed'.
  real(dp) :: psi, fric_const1, dtdx1, fric_const2, dtdx2,              &
                   fric_const3, dtdx3, fric_const4, dtdx4,              &
              c_M1, u_M1, c_L1, u_L1, area1, d_h1, roughness1,          &
              rr1, rr371, stag_1, JFTRdrag1,                            &
              c_M2, u_M2, c_L2, u_L2, area2, d_h2, roughness2,          &
              rr2, rr372, stag_2, JFTRdrag2,                            &
              c_M3, u_M3, c_L3, u_L3, area3, d_h3, roughness3,          &
              rr3, rr373, stag_3, JFTRdrag3,                            &
              c_M4, u_M4, c_L4, u_L4, area4, d_h4, roughness4,          &
              rr4, rr374, stag_4, JFTRdrag4
  integer (kind=8) :: fric_app_num

  ! Identify the values returned by the routine.
  real (dp), intent(out) :: char1, char2, char3, char4, continuity,     &
                            P_stag1, P_stag2, P_stag3

  ! Define the intermediate variables.
  real(dp) :: c_f1, u_f1, Fanning_1, E_1dt, stag1_term,                 &
              c_f2, u_f2, Fanning_2, E_2dt,                             &
              c_f3, u_f3, Fanning_3, E_3dt,                             &
              c_f4, u_f4, Fanning_4, E_4dt

  ! Define the types of values returned by Fortran functions.
  real(dp) :: fricfac

  ! Unpack all the values in arrays into suitably-named variables.
  c_N1 = varies(1)
  u_N1 = varies(2)
  c_N2 = varies(3)
  u_N2 = varies(4)
  c_N3 = varies(5)
  u_N3 = varies(6)
  c_N4 = varies(7)
  u_N4 = varies(8)

  psi = fixed(1)
  fric_app_num = int(fixed(2))
  dtdx1 = fixed(3)
  area1 = fixed(4)
  d_h1 = fixed(5)
  rr1 =  fixed(6)
  rr371 =  fixed(7)
  fric_const1 = fixed(8)
  roughness1 = fixed(9)
  stag_1 = fixed(10)
  JFTRdrag1 = fixed(11)
  c_M1 = fixed(12)
  u_M1 = fixed(13)
  c_L1 = fixed(14)
  u_L1 = fixed(15)
  dtdx2 = fixed(16)
  area2 = fixed(17)
  d_h2 = fixed(18)
  rr2 =  fixed(19)
  rr372 =  fixed(20)
  fric_const2 = fixed(21)
  roughness2 = fixed(22)
  stag_2 = fixed(23)
  JFTRdrag2 = fixed(24)
  c_M2 = fixed(25)
  u_M2 = fixed(26)
  c_L2 = fixed(27)
  u_L2 = fixed(28)
  dtdx3 = fixed(29)
  area3 = fixed(30)
  d_h3 = fixed(31)
  rr3 =  fixed(32)
  rr373 =  fixed(33)
  fric_const3 = fixed(34)
  roughness3 = fixed(35)
  stag_3 = fixed(36)
  JFTRdrag3 = fixed(37)
  c_M3 = fixed(38)
  u_M3 = fixed(39)
  c_L3 = fixed(40)
  u_L3 = fixed(41)
  dtdx4 = fixed(42)
  area4 = fixed(43)
  d_h4 = fixed(44)
  rr4 =  fixed(45)
  rr374 =  fixed(46)
  fric_const4 = fixed(47)
  roughness4 = fixed(48)
  stag_4 = fixed(49)
  JFTRdrag4 = fixed(50)
  c_M4 = fixed(51)
  u_M4 = fixed(52)
  c_L4 = fixed(53)
  u_L4 = fixed(54)

  ! Get the conditions at the base of the forwards characteristics
  call basefwd1(dtdx1, c_M1, u_M1, c_L1, u_L1, c_N1, u_N1, c_f1, u_f1)
  call basefwd1(dtdx2, c_M2, u_M2, c_L2, u_L2, c_N2, u_N2, c_f2, u_f2)
  call basefwd1(dtdx3, c_M3, u_M3, c_L3, u_L3, c_N3, u_N3, c_f3, u_f3)
  call basefwd1(dtdx4, c_M4, u_M4, c_L4, u_L4, c_N4, u_N4, c_f4, u_f4)

  ! Calculate the Fanning friction factors for these velocities.
  Fanning_1 = fricfac(d_h1, roughness1, rr1, rr371, u_f1, fric_app_num)
  Fanning_2 = fricfac(d_h2, roughness2, rr2, rr372, u_f2, fric_app_num)
  Fanning_3 = fricfac(d_h3, roughness3, rr3, rr373, u_f3, fric_app_num)
  Fanning_4 = fricfac(d_h4, roughness4, rr4, rr374, u_f4, fric_app_num)

  ! Get new values of the friction, jet fan and traffic terms.
  E_1dt = fric_const1 * Fanning_1 * u_f1 * abs(u_f1) + JFTRdrag1
  E_2dt = fric_const2 * Fanning_2 * u_f2 * abs(u_f2) + JFTRdrag2
  E_3dt = fric_const3 * Fanning_3 * u_f3 * abs(u_f3) + JFTRdrag3
  E_4dt = fric_const4 * Fanning_4 * u_f4 * abs(u_f4) + JFTRdrag4

  ! Define functions for the four characteristics.  These all
  ! should equal zero.
  char1 = psi * (c_N1 - c_f1) + (u_N1 - u_f1) + E_1dt
  char2 = psi * (c_N2 - c_f2) + (u_N2 - u_f2) + E_2dt
  char3 = psi * (c_N3 - c_f3) + (u_N3 - u_f3) + E_3dt
  char4 = psi * (c_N4 - c_f4) + (u_N4 - u_f4) + E_4dt

  ! Define the continuity equation for compressible flow.  The way
  ! the signs of the velocities are set up means that this should
  ! also equal zero.
  continuity = area1 * u_N1 * (c_N1/c_N2)**psi + area2 * u_N2           &
             + area3 * u_N3 * (c_N3/c_N2)**psi                          &
             + area4 * u_N4 * (c_N4/c_N2)**psi

  ! There are terms in the stagnation pressure equations that we use
  ! in more than one equation.  Put them into one variable.
  stag1_term = c_N1**2 + stag_1 * u_N1**2

  ! Define three equations giving the difference between the stagnation
  ! pressures in three pairs of the gridpoints at the node.
  P_stag1 = stag1_term - c_N2**2 - stag_2*u_N2**2
  P_stag2 = stag1_term - c_N3**2 - stag_3*u_N3**2
  P_stag3 = stag1_term - c_N4**2 - stag_4*u_N4**2

  return
end subroutine fourwaymoc2a


subroutine fivewaymoc2a(varies, fixed, char1, char2, char3, char4,      &
                       char5, continuity, P_stag1, P_stag2, P_stag3,    &
                       P_stag4)
  ! Define ten equations that need to be satisfied to calculate new
  ! values of celerity and velocity at points in five cells at a
  ! five-way junction.  These are:
  !  * five forward characteristics in the five cells,
  !  * one mass continuity equation at the node, and
  !  * four calculations of differences between stagnation pressure
  !    at the node.

  implicit none
  integer, parameter :: dp=kind(0.d0)
  ! Define the values being passed in.
  real(dp), dimension(10), intent(in) :: varies
  real(dp), dimension(67), intent(in) :: fixed

  ! First define the ten values that scipy.optimize.fsolve varies, these
  ! are passed in 'varies'.
  real(dp) :: c_N1, u_N1, c_N2, u_N2, c_N3, u_N3, c_N4, u_N4, c_N5, u_N5

  ! Next define the genuine constants, these are passed in 'fixed'.
  real(dp) :: psi, fric_const1, dtdx1, fric_const2, dtdx2,              &
                   fric_const3, dtdx3, fric_const4, dtdx4,              &
                   fric_const5, dtdx5,                                  &
              c_M1, u_M1, c_L1, u_L1, area1, d_h1, roughness1,          &
              rr1, rr371, stag_1, JFTRdrag1,                            &
              c_M2, u_M2, c_L2, u_L2, area2, d_h2, roughness2,          &
              rr2, rr372, stag_2, JFTRdrag2,                            &
              c_M3, u_M3, c_L3, u_L3, area3, d_h3, roughness3,          &
              rr3, rr373, stag_3, JFTRdrag3,                            &
              c_M4, u_M4, c_L4, u_L4, area4, d_h4, roughness4,          &
              rr4, rr374, stag_4, JFTRdrag4,                            &
              c_M5, u_M5, c_L5, u_L5, area5, d_h5, roughness5,          &
              rr5, rr375, stag_5, JFTRdrag5
  integer (kind=8) :: fric_app_num

  ! Identify the values returned by the routine.
  real (dp), intent(out) :: char1, char2, char3, char4, char5, continuity, &
                            P_stag1, P_stag2, P_stag3, P_stag4

  ! Define the intermediate variables.
  real(dp) :: c_f1, u_f1, Fanning_1, E_1dt, stag1_term,                 &
              c_f2, u_f2, Fanning_2, E_2dt,                             &
              c_f3, u_f3, Fanning_3, E_3dt,                             &
              c_f4, u_f4, Fanning_4, E_4dt,                             &
              c_f5, u_f5, Fanning_5, E_5dt

  ! Define the types of values returned by Fortran functions.
  real(dp) :: fricfac

  ! Unpack all the values in arrays into suitably-named variables.
  c_N1 = varies(1)
  u_N1 = varies(2)
  c_N2 = varies(3)
  u_N2 = varies(4)
  c_N3 = varies(5)
  u_N3 = varies(6)
  c_N4 = varies(7)
  u_N4 = varies(8)
  c_N5 = varies(9)
  u_N5 = varies(10)

  psi = fixed(1)
  fric_app_num = int(fixed(2))
  dtdx1 = fixed(3)
  area1 = fixed(4)
  d_h1 = fixed(5)
  rr1 =  fixed(6)
  rr371 =  fixed(7)
  fric_const1 = fixed(8)
  roughness1 = fixed(9)
  stag_1 = fixed(10)
  JFTRdrag1 = fixed(11)
  c_M1 = fixed(12)
  u_M1 = fixed(13)
  c_L1 = fixed(14)
  u_L1 = fixed(15)
  dtdx2 = fixed(16)
  area2 = fixed(17)
  d_h2 = fixed(18)
  rr2 =  fixed(19)
  rr372 =  fixed(20)
  fric_const2 = fixed(21)
  roughness2 = fixed(22)
  stag_2 = fixed(23)
  JFTRdrag2 = fixed(24)
  c_M2 = fixed(25)
  u_M2 = fixed(26)
  c_L2 = fixed(27)
  u_L2 = fixed(28)
  dtdx3 = fixed(29)
  area3 = fixed(30)
  d_h3 = fixed(31)
  rr3 =  fixed(32)
  rr373 =  fixed(33)
  fric_const3 = fixed(34)
  roughness3 = fixed(35)
  stag_3 = fixed(36)
  JFTRdrag3 = fixed(37)
  c_M3 = fixed(38)
  u_M3 = fixed(39)
  c_L3 = fixed(40)
  u_L3 = fixed(41)
  dtdx4 = fixed(42)
  area4 = fixed(43)
  d_h4 = fixed(44)
  rr4 =  fixed(45)
  rr374 =  fixed(46)
  fric_const4 = fixed(47)
  roughness4 = fixed(48)
  stag_4 = fixed(49)
  JFTRdrag4 = fixed(50)
  c_M4 = fixed(51)
  u_M4 = fixed(52)
  c_L4 = fixed(53)
  u_L4 = fixed(54)
  dtdx5 = fixed(55)
  area5 = fixed(56)
  d_h5 = fixed(57)
  rr5 = fixed(58)
  rr375 =  fixed(59)
  fric_const5 = fixed(60)
  roughness5 = fixed(61)
  stag_5 = fixed(62)
  JFTRdrag5 = fixed(63)
  c_M5 = fixed(64)
  u_M5 = fixed(65)
  c_L5 = fixed(66)
  u_L5 = fixed(67)

  ! Get the conditions at the base of the forwards characteristics
  call basefwd1(dtdx1, c_M1, u_M1, c_L1, u_L1, c_N1, u_N1, c_f1, u_f1)
  call basefwd1(dtdx2, c_M2, u_M2, c_L2, u_L2, c_N2, u_N2, c_f2, u_f2)
  call basefwd1(dtdx3, c_M3, u_M3, c_L3, u_L3, c_N3, u_N3, c_f3, u_f3)
  call basefwd1(dtdx4, c_M4, u_M4, c_L4, u_L4, c_N4, u_N4, c_f4, u_f4)
  call basefwd1(dtdx5, c_M5, u_M5, c_L5, u_L5, c_N5, u_N5, c_f5, u_f5)

  ! Calculate the Fanning friction factors for these velocities.
  Fanning_1 = fricfac(d_h1, roughness1, rr1, rr371, u_f1, fric_app_num)
  Fanning_2 = fricfac(d_h2, roughness2, rr2, rr372, u_f2, fric_app_num)
  Fanning_3 = fricfac(d_h3, roughness3, rr3, rr373, u_f3, fric_app_num)
  Fanning_4 = fricfac(d_h4, roughness4, rr4, rr374, u_f4, fric_app_num)
  Fanning_5 = fricfac(d_h5, roughness5, rr5, rr375, u_f5, fric_app_num)

  ! Get new values of the friction, jet fan and traffic terms.
  E_1dt = fric_const1 * Fanning_1 * u_f1 * abs(u_f1) + JFTRdrag1
  E_2dt = fric_const2 * Fanning_2 * u_f2 * abs(u_f2) + JFTRdrag2
  E_3dt = fric_const3 * Fanning_3 * u_f3 * abs(u_f3) + JFTRdrag3
  E_4dt = fric_const4 * Fanning_4 * u_f4 * abs(u_f4) + JFTRdrag4
  E_5dt = fric_const5 * Fanning_5 * u_f5 * abs(u_f5) + JFTRdrag5

  ! Define functions for the five characteristics.  These all
  ! should equal zero.
  char1 = psi * (c_N1 - c_f1) + (u_N1 - u_f1) + E_1dt
  char2 = psi * (c_N2 - c_f2) + (u_N2 - u_f2) + E_2dt
  char3 = psi * (c_N3 - c_f3) + (u_N3 - u_f3) + E_3dt
  char4 = psi * (c_N4 - c_f4) + (u_N4 - u_f4) + E_4dt
  char5 = psi * (c_N5 - c_f5) + (u_N5 - u_f5) + E_5dt

  ! Define the continuity equation for compressible flow.  The way
  ! the signs of the velocities are set up means that this should
  ! also equal zero.
  continuity = area1 * u_N1 * (c_N1/c_N2)**psi + area2 * u_N2           &
             + area3 * u_N3 * (c_N3/c_N2)**psi                          &
             + area4 * u_N4 * (c_N4/c_N2)**psi                          &
             + area5 * u_N5 * (c_N5/c_N2)**psi

  ! There are terms in the stagnation pressure equations that we use
  ! in more than one equation.  Put them into one variable.
  stag1_term = c_N1**2 + stag_1 * u_N1**2

  ! Define four equations giving the difference between the stagnation
  ! pressures in four pairs of the gridpoints at the node.
  P_stag1 = stag1_term - c_N2**2 - stag_2*u_N2**2
  P_stag2 = stag1_term - c_N3**2 - stag_3*u_N3**2
  P_stag3 = stag1_term - c_N4**2 - stag_4*u_N4**2
  P_stag4 = stag1_term - c_N5**2 - stag_5*u_N5**2

  return
end subroutine fivewaymoc2a


subroutine sixwaymoc2a(varies, fixed, char1, char2, char3, char4,       &
                       char5, char6, continuity, P_stag1, P_stag2,      &
                       P_stag3, P_stag4, P_stag5)
  ! Define 12 equations that need to be satisfied to calculate new
  ! values of celerity and velocity at points in six cells at a
  ! six-way junction.  These are:
  !  * six forward characteristics in the six cells,
  !  * one mass continuity equation at the node, and
  !  * five calculations of differences between stagnation pressure
  !    at the node.

  implicit none
  integer, parameter :: dp=kind(0.d0)
  ! Define the values being passed in.
  real(dp), dimension(12), intent(in) :: varies
  real(dp), dimension(80), intent(in) :: fixed

  ! First define the twelve values that scipy.optimize.fsolve varies,
  ! these are passed in 'varies'.
  real(dp) :: c_N1, u_N1, c_N2, u_N2, c_N3, u_N3, c_N4, u_N4,           &
              c_N5, u_N5, c_N6, u_N6

  ! Next define the genuine constants, these are passed in 'fixed'.
  real(dp) :: psi, fric_const1, dtdx1, fric_const2, dtdx2,              &
                   fric_const3, dtdx3, fric_const4, dtdx4,              &
                   fric_const5, dtdx5, fric_const6, dtdx6,              &
              c_M1, u_M1, c_L1, u_L1, area1, d_h1, roughness1,          &
              rr1, rr371, stag_1, JFTRdrag1,                            &
              c_M2, u_M2, c_L2, u_L2, area2, d_h2, roughness2,          &
              rr2, rr372, stag_2, JFTRdrag2,                            &
              c_M3, u_M3, c_L3, u_L3, area3, d_h3, roughness3,          &
              rr3, rr373, stag_3, JFTRdrag3,                            &
              c_M4, u_M4, c_L4, u_L4, area4, d_h4, roughness4,          &
              rr4, rr374, stag_4, JFTRdrag4,                            &
              c_M5, u_M5, c_L5, u_L5, area5, d_h5, roughness5,          &
              rr5, rr375, stag_5, JFTRdrag5,                            &
              c_M6, u_M6, c_L6, u_L6, area6, d_h6, roughness6,          &
              rr6, rr376, stag_6, JFTRdrag6
  integer (kind=8) :: fric_app_num

  ! Identify the values returned by the routine.
  real (dp), intent(out) :: char1, char2, char3, char4, char5, char6,   &
                            continuity, P_stag1, P_stag2, P_stag3,      &
                            P_stag4, P_stag5

  ! Define the intermediate variables.
  real(dp) :: c_f1, u_f1, Fanning_1, E_1dt, stag1_term,                 &
              c_f2, u_f2, Fanning_2, E_2dt,                             &
              c_f3, u_f3, Fanning_3, E_3dt,                             &
              c_f4, u_f4, Fanning_4, E_4dt,                             &
              c_f5, u_f5, Fanning_5, E_5dt,                             &
              c_f6, u_f6, Fanning_6, E_6dt

  ! Define the types of values returned by Fortran functions.
  real(dp) :: fricfac

  ! Unpack all the values in arrays into suitably-named variables.
  c_N1 = varies(1)
  u_N1 = varies(2)
  c_N2 = varies(3)
  u_N2 = varies(4)
  c_N3 = varies(5)
  u_N3 = varies(6)
  c_N4 = varies(7)
  u_N4 = varies(8)
  c_N5 = varies(9)
  u_N5 = varies(10)
  c_N6 = varies(11)
  u_N6 = varies(12)

  psi = fixed(1)
  fric_app_num = int(fixed(2))
  dtdx1 = fixed(3)
  area1 = fixed(4)
  d_h1 = fixed(5)
  rr1 =  fixed(6)
  rr371 =  fixed(7)
  fric_const1 = fixed(8)
  roughness1 = fixed(9)
  stag_1 = fixed(10)
  JFTRdrag1 = fixed(11)
  c_M1 = fixed(12)
  u_M1 = fixed(13)
  c_L1 = fixed(14)
  u_L1 = fixed(15)
  dtdx2 = fixed(16)
  area2 = fixed(17)
  d_h2 = fixed(18)
  rr2 =  fixed(19)
  rr372 =  fixed(20)
  fric_const2 = fixed(21)
  roughness2 = fixed(22)
  stag_2 = fixed(23)
  JFTRdrag2 = fixed(24)
  c_M2 = fixed(25)
  u_M2 = fixed(26)
  c_L2 = fixed(27)
  u_L2 = fixed(28)
  dtdx3 = fixed(29)
  area3 = fixed(30)
  d_h3 = fixed(31)
  rr3 =  fixed(32)
  rr373 =  fixed(33)
  fric_const3 = fixed(34)
  roughness3 = fixed(35)
  stag_3 = fixed(36)
  JFTRdrag3 = fixed(37)
  c_M3 = fixed(38)
  u_M3 = fixed(39)
  c_L3 = fixed(40)
  u_L3 = fixed(41)
  dtdx4 = fixed(42)
  area4 = fixed(43)
  d_h4 = fixed(44)
  rr4 =  fixed(45)
  rr374 =  fixed(46)
  fric_const4 = fixed(47)
  roughness4 = fixed(48)
  stag_4 = fixed(49)
  JFTRdrag4 = fixed(50)
  c_M4 = fixed(51)
  u_M4 = fixed(52)
  c_L4 = fixed(53)
  u_L4 = fixed(54)
  dtdx5 = fixed(55)
  area5 = fixed(56)
  d_h5 = fixed(57)
  rr5 = fixed(58)
  rr375 =  fixed(59)
  fric_const5 = fixed(60)
  roughness5 = fixed(61)
  stag_5 = fixed(62)
  JFTRdrag5 = fixed(63)
  c_M5 = fixed(64)
  u_M5 = fixed(65)
  c_L5 = fixed(66)
  u_L5 = fixed(67)
  dtdx6 = fixed(68)
  area6 = fixed(69)
  d_h6 = fixed(70)
  rr6 = fixed(71)
  rr376 =  fixed(72)
  fric_const6 = fixed(73)
  roughness6 = fixed(74)
  stag_6 = fixed(75)
  JFTRdrag6 = fixed(76)
  c_M6 = fixed(77)
  u_M6 = fixed(78)
  c_L6 = fixed(79)
  u_L6 = fixed(80)

  ! Get the conditions at the base of the forwards characteristics
  call basefwd1(dtdx1, c_M1, u_M1, c_L1, u_L1, c_N1, u_N1, c_f1, u_f1)
  call basefwd1(dtdx2, c_M2, u_M2, c_L2, u_L2, c_N2, u_N2, c_f2, u_f2)
  call basefwd1(dtdx3, c_M3, u_M3, c_L3, u_L3, c_N3, u_N3, c_f3, u_f3)
  call basefwd1(dtdx4, c_M4, u_M4, c_L4, u_L4, c_N4, u_N4, c_f4, u_f4)
  call basefwd1(dtdx5, c_M5, u_M5, c_L5, u_L5, c_N5, u_N5, c_f5, u_f5)
  call basefwd1(dtdx6, c_M6, u_M6, c_L6, u_L6, c_N6, u_N6, c_f6, u_f6)

  ! Calculate the Fanning friction factors for these velocities.
  Fanning_1 = fricfac(d_h1, roughness1, rr1, rr371, u_f1, fric_app_num)
  Fanning_2 = fricfac(d_h2, roughness2, rr2, rr372, u_f2, fric_app_num)
  Fanning_3 = fricfac(d_h3, roughness3, rr3, rr373, u_f3, fric_app_num)
  Fanning_4 = fricfac(d_h4, roughness4, rr4, rr374, u_f4, fric_app_num)
  Fanning_5 = fricfac(d_h5, roughness5, rr5, rr375, u_f5, fric_app_num)
  Fanning_6 = fricfac(d_h6, roughness6, rr6, rr376, u_f6, fric_app_num)

  ! Get new values of the friction, jet fan and traffic terms.
  E_1dt = fric_const1 * Fanning_1 * u_f1 * abs(u_f1) + JFTRdrag1
  E_2dt = fric_const2 * Fanning_2 * u_f2 * abs(u_f2) + JFTRdrag2
  E_3dt = fric_const3 * Fanning_3 * u_f3 * abs(u_f3) + JFTRdrag3
  E_4dt = fric_const4 * Fanning_4 * u_f4 * abs(u_f4) + JFTRdrag4
  E_5dt = fric_const5 * Fanning_5 * u_f5 * abs(u_f5) + JFTRdrag5
  E_6dt = fric_const6 * Fanning_6 * u_f6 * abs(u_f6) + JFTRdrag6

  ! Define functions for the six characteristics.  These all
  ! should equal zero.
  char1 = psi * (c_N1 - c_f1) + (u_N1 - u_f1) + E_1dt
  char2 = psi * (c_N2 - c_f2) + (u_N2 - u_f2) + E_2dt
  char3 = psi * (c_N3 - c_f3) + (u_N3 - u_f3) + E_3dt
  char4 = psi * (c_N4 - c_f4) + (u_N4 - u_f4) + E_4dt
  char5 = psi * (c_N5 - c_f5) + (u_N5 - u_f5) + E_5dt
  char6 = psi * (c_N6 - c_f6) + (u_N6 - u_f6) + E_6dt

  ! Define the continuity equation for compressible flow.  The way
  ! the signs of the velocities are set up means that this should
  ! also equal zero.
  continuity = area1 * u_N1 * (c_N1/c_N2)**psi + area2 * u_N2           &
             + area3 * u_N3 * (c_N3/c_N2)**psi                          &
             + area4 * u_N4 * (c_N4/c_N2)**psi                          &
             + area5 * u_N5 * (c_N5/c_N2)**psi                          &
             + area6 * u_N6 * (c_N6/c_N2)**psi

  ! There are terms in the stagnation pressure equations that we use
  ! in more than one equation.  Put them into one variable.
  stag1_term = c_N1**2 + stag_1 * u_N1**2

  ! Define five equations giving the difference between the stagnation
  ! pressures in five pairs of the gridpoints at the node.
  P_stag1 = stag1_term - c_N2**2 - stag_2*u_N2**2
  P_stag2 = stag1_term - c_N3**2 - stag_3*u_N3**2
  P_stag3 = stag1_term - c_N4**2 - stag_4*u_N4**2
  P_stag4 = stag1_term - c_N5**2 - stag_5*u_N5**2
  P_stag5 = stag1_term - c_N6**2 - stag_6*u_N6**2

  return
end subroutine sixwaymoc2a


subroutine twowaymoc2fan(varies, fixed, char1, char2, continuity, P_stag)
  ! It calculates the fan pressure rise from two fan characteristics
  ! (forwards and reverse) and a list of variation of times and fan
  ! speeds.
  ! Define four equations that need to be satisfied to calculate new
  ! values of celerity and velocity on each side of a fan junction.
  ! These are:
  !  * one forwards characteristic in the cell before the fan,
  !  * one backwards characteristic in the cell before the fan,
  !  * one mass continuity equation at the node, and
  !  * the difference between stagnation pressures at both sides of
  !    the node.
  ! All four equations are expressed in a way that makes their desired
  ! result zero, so that scipy.optimize.fsolve can solve the system of
  ! equations by varying four values.
  !
  ! The stagnation pressure factors may vary with time as the fan runs
  ! up and down.  They may also vary as the system characteristic seen
  ! by the fan changes and the fan moves to a different duty point on
  ! its characteristic.
  !
  ! The 'fixed' array contains some weird stuff.  All the routines that
  ! calculate joins or area changes have it as a fixed-length array.
  ! But in the fans we need to pass the fan characteristic, which is of
  ! variable length.  As far as I can tell we can't pass more than one
  ! 'fixed' array, so we'll have 25 entries for the fixed data, the 26th
  ! entry will be the count of entries in the fan characteristic (call
  ! it 'fcount' for short), the next 'fcount' entries will be the flow
  ! values and the 'fcount' entries after that will be the corresponding
  ! total pressure rise values.  There is probably a better way but I
  ! could spend weeks figuring it out, so this is how it's going to be
  ! kludged.

  implicit none
  integer, parameter :: dp=kind(0.d0)
  ! Define the values being passed in.
  real(dp), dimension(4), intent(in) :: varies
  real(dp), dimension(*), intent(in) :: fixed

  ! First define the four values that scipy.optimize.fsolve varies, these
  ! are passed in 'varies'.
  real(dp) :: c_N1, u_N1, c_N2, u_N2

  ! Next define the genuine constants, these are passed in 'fixed'.
  real(dp) :: psi, fric_const1, dtdx1, fric_const2, dtdx2,              &
              c_M1, u_M1, c_L, u_L, area1, d_h1, roughness1, rr1,       &
              rr371, stag_1, JFTRdrag1,                                 &
              c_M2, u_M2, c_R, u_R, area2, d_h2, roughness2, rr2,       &
              rr372, stag_2, JFTRdrag2,                                 &
              speed
  integer (kind=8) :: fric_app_num, fcount, bound2, bound3, bound4

  ! Identify the values returned by the routine.
  real (dp), intent(out) :: char1, char2, continuity, P_stag

  ! Define the intermediate variables.
  real(dp) :: c_f1, u_f1, Fanning_1, E_1dt, c_b2, u_b2, Fanning_2, E_2dt, &
              c_fansq

  ! Define the types of values returned by Fortran functions.
  real(dp) :: fricfac, extrapolate

  ! Unpack all the values in arrays into suitably-named variables.
  c_N1 = varies(1)
  u_N1 = varies(2)
  c_N2 = varies(3)
  u_N2 = varies(4)

  psi = fixed(1)
  fric_app_num = int(fixed(2))
  dtdx1 = fixed(3)
  area1 = fixed(4)
  d_h1 = fixed(5)
  rr1 =  fixed(6)
  rr371 =  fixed(7)
  fric_const1 = fixed(8)
  roughness1 = fixed(9)
  stag_1 = fixed(10)
  JFTRdrag1 = fixed(11)
  c_M1 = fixed(12)
  u_M1 = fixed(13)
  c_L = fixed(14)
  u_L = fixed(15)
  dtdx2 = fixed(16)
  area2 = fixed(17)
  d_h2 = fixed(18)
  rr2 =  fixed(19)
  rr372 =  fixed(20)
  fric_const2 = fixed(21)
  roughness2 = fixed(22)
  stag_2 = fixed(23)
  JFTRdrag2 = fixed(24)
  c_M2 = fixed(25)
  u_M2 = fixed(26)
  c_R = fixed(27)
  u_R = fixed(28)

  ! Get the conditions at the base of the forwards characteristic
  ! in the first cell.
  call basefwd1(dtdx1, c_M1, u_M1, c_L, u_L, c_N1, u_N1, c_f1, u_f1)
  ! Get the conditions at the base of the backwards characteristic
  ! in the second cell.
  call baseback1(dtdx2, c_M2, u_M2, c_R, u_R, c_N2, u_N2, c_b2, u_b2)

  ! Calculate the Fanning friction factors for these velocities.
  Fanning_1 = fricfac(d_h1, roughness1, rr1, rr371, u_f1, fric_app_num)
  Fanning_2 = fricfac(d_h2, roughness2, rr2, rr372, u_b2, fric_app_num)

  ! Get new values of the friction terms.
  E_1dt = fric_const1 * Fanning_1 * u_f1 * abs(u_f1) + JFTRdrag1
  E_2dt = fric_const2 * Fanning_2 * u_b2 * abs(u_b2) + JFTRdrag2

  ! Define functions for the forwards characteristic and the backward
  ! characteristic.  These both should equal zero.
  char1 = psi * (c_N1 - c_f1) + (u_N1 - u_f1) + E_1dt
  char2 = psi * (c_N2 - c_b2) - (u_N2 - u_b2) - E_2dt

  ! Define the continuity equation for compressible flow.  The way
  ! the signs of the velocities are set up means that this should
  ! also equal zero.
  continuity = u_N1 * (c_N1/c_N2)**psi - u_N2

  ! Get the duty point of the fan at the current timestep.  We take
  ! the value of u_N1 and find a fan pressure rise (c^2 in m^2/s^2)
  ! that matches it.  As scipy.optimize.fsolve calculates, the fan
  ! characteristic will move to the appropriate value of c^2 that
  ! corresponds to the velocity at the fan inlet, which is u_N1 if
  ! the fan speed is positive) or u_N2 (if the fan speed is negative).
  speed = fixed(29)
  fcount = int(fixed(30))
  bound2 = 30 + fcount
  bound3 = bound2 + 1
  bound4 = bound2 + fcount - 1
  if (abs(speed) < 0.000000001_dp) then
      ! The fan is turned off (speed zero).  Set the fan total pressure
      ! rise to zero.
      c_fansq = 0.0
  elseif (speed .gt. 0.0) then
    ! The fan is in forwards mode, so u_N1 is the velocity at the fan inlet.
    !
    ! The weird limits below pick out where the flows and pressure rises
    ! of the fan's characteristic are inside the array 'fixed'.
    c_fansq = extrapolate(u_N1, fcount, fixed(  31  : bound2), &
                                        fixed(bound3: bound4))
  else
    ! The fan is in reverse mode, so u_N2 is the velocity entering the
    ! fan inlet.
    c_fansq = extrapolate(u_N2, fcount, fixed(  31  : bound2), &
                                        fixed(bound3: bound4))
  end if

  ! Define an equation giving the difference between the stagnation
  ! pressure at N1 and the stagnation pressure at N2.  This should
  ! be zero.
  P_stag =  c_N1**2 + c_fansq + stag_1  * u_N1**2   &
          - c_N2**2           - stag_2  * u_N2**2
  return
end subroutine twowaymoc2fan


subroutine trafficadjust(dists, vels, TRcalc_data, gpoints, blocks, local_drags)
  ! Take the segment-based definitions of traffic, the current
  ! calculation time, the distances along the tunnels and the
  ! air velocities in the tunnels at the previous timestep.
  ! Calculate the traffic drag in each cell, using the air
  ! velocities at the ends of the cells in the previous timestep.
  ! Return a list of np.arrays that have the traffic drag expressed
  ! as m**2/s**2 per metre length of each cell.

  implicit none
  integer, parameter :: dp=kind(0.d0)
  ! Define the values being passed in and out.
  integer (kind=8), intent(in) :: gpoints, blocks
  real(dp), dimension(gpoints), intent(in) :: dists, vels
  real(dp), dimension(blocks, 4), intent(in) :: TRcalc_data
  real(dp), dimension(gpoints - 1), intent(out) :: local_drags

  ! Define some interim variables
  integer (kind=8) :: ii, iii, iip1    ! Loop counters
  real(dp) :: start, stop, back, fwd, length, tr_start, tr_stop, v_diff

  ! Get the cell length.  All the cells are the same length so we
  ! do this outside the loop
  length = dists(2) - dists(1)

  ! Loop over each cell
  do ii = 1, gpoints - 1
    iip1 = ii + 1
    back = dists(ii)
    fwd =  dists(iip1)
    ! Loop over each block of traffic
    do iii = 1, blocks
      ! A note to anyone trying to figure this routine out: a more
      ! detailed explanation can be found in the Python function
      ! called "TRTimeAdjust" that this routine is called from.
      start = TRcalc_data(iii, 1)
      stop = TRcalc_data(iii, 2)
      if (start < fwd .and. stop > back) then
        tr_start = max(start, back)
        tr_stop = min(stop, fwd)
        v_diff = TRcalc_data(iii, 3) - ( (vels(ii) + vels(iip1)) / 2 )
        ! Add the drag of traffic in this block to the cell's traffic drag.
        local_drags(ii) = local_drags(ii) - (tr_stop - tr_start) / length &
                          * TRcalc_data(iii, 4) * v_diff * abs(v_diff)
      end if
    end do
  end do
  return
end subroutine trafficadjust




