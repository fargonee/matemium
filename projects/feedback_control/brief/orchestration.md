# Orchestration — Feedback Control

- Landscape 16:9; begin in one persistent 3D road-and-vehicle world.
- Build the physical world in native `z`-up coordinates. Keep every vehicle
  camera above the road and on the negative-y roadside; do not orbit through
  or beneath the terrain.
- Gold is target, blue measured speed, red error, mint command, and orange hill
  load across every representation.
- Reveal physical callouts causally: target and hill load, then sensor and
  measurement, then measured speed and throttle correction. Never display all
  callouts at once.
- Observe the same road position and physical time first without feedback and
  then with the balanced controller.
- Alternate the physical world with isolated dashboard and causal-loop tapes;
  do not overlay a tape on the vehicle.
- Advance the balanced world to recovery and move the response cursor to the
  same explicit simulation time.
- Compare slow, balanced, aggressive, and open cases on identical axes and with
  the same disturbance time.
- End by returning to the road before the final loop synthesis.
- Coordination is deterministic and timestamped but does not claim a generic
  continuously reactive engine clock.
