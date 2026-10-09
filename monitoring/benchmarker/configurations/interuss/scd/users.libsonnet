local flights = import '../flights.libsonnet';
local s2_expand_latlng_rect = std.native('s2.expand_latlng_rect');

{
  basic_scd_behavior: function(dss_pool, sub_id, accept_notice, activate_notice, coordination_group='cluster1') {
    dss_pool: dss_pool,
    dss_selection_strategy: 'Random',
    subscription_strategy: {
      single_subscription: {
        subscription_id: sub_id,
      },
    },
    op_intent_ref_creation_strategy: {
      ovn_coordination_group: coordination_group,
      coordinate_requested_ovns: true,
      retries: 2,
      accept_before_flight_start: accept_notice,
      activate_before_flight_start: activate_notice,
      expect_timely_clearance: true,
    },
    op_intent_ref_cleanup_strategy: {
      after_actual_flight_end: '1s',
    },
  },

  // Keep the whole flight footprint inside the subscription's rectangle.
  basic_flight_planner: function(dss_pool, sub_id, rect, lat_size, lng_size, coordination_group='cluster1') {
    flight_generation: {
      independent_time_location_shape: {
        time: {
          fixed_spacing: '36s',
          uniform_random_spacing: '7.2s',
        },
        location: flights.laglng_rect_location(s2_expand_latlng_rect(rect, -lat_size, -lng_size)),
        shape: flights.latlng_rect_shape(lat_size, lng_size),
      },
    },
    flight_execution: {
      end_flight_after_start: '5s',
    },
    scd_behavior: $.basic_scd_behavior(dss_pool, sub_id, '20s', '10s', coordination_group),
  },
}
