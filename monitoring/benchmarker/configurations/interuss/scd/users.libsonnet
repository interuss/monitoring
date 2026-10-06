{
  basic_scd_behavior: function(dss_pool, sub_id, accept_notice, activate_notice) {
    dss_pool: dss_pool,
    dss_selection_strategy: 'Random',
    subscription_strategy: {
      single_subscription: {
        subscription_id: sub_id,
      },
    },
    op_intent_ref_creation_strategy: {
      ovn_coordination_group: 'cluster1',
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

}
