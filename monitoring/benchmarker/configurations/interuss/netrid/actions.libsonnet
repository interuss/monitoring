{
  create_subscription: function(name, sub_id) {
    name: name,
    f3411: {
      create_subscription: {
        subscription: {
          subscription_id: sub_id,
          rid_version: 'F3411-22a',
          duration: '23h',
          area: {
            lat_min: 34 - 0.00001,
            lng_min: -118 - 0.00001,
            lat_max: 34 + 0.00001,
            lng_max: -118 + 0.00001,
          },
          min_alt: {value: 0, units: 'M', reference: 'W84'},
          max_alt: {value: 3000, units: 'M', reference: 'W84'},
        },
        mode: 'GetDeleteCreate',
      },
    },
  },

  delete_subscription: function(name, sub_id) {
    name: name,
    f3411: {
      delete_subscription: {
        subscription_id: sub_id,
        mode: 'GetDeleteIfExist',
      },
    },
  },
}
