local s2_latlng_rect_part = std.native('s2.latlng_rect_part');

{
  create_subscription: function(name, sub_id, rect) {
    name: name,
    f3548: {
      create_subscription: {
        subscription: {
          subscription_id: sub_id,
          duration: '23h',
          area: {
            lat_min: s2_latlng_rect_part(rect, 'lat_lo'),
            lng_min: s2_latlng_rect_part(rect, 'lng_lo'),
            lat_max: s2_latlng_rect_part(rect, 'lat_hi'),
            lng_max: s2_latlng_rect_part(rect, 'lng_hi'),
          },
          min_alt: {value: 0, units: 'M', reference: 'W84'},
          max_alt: {value: 3000, units: 'M', reference: 'W84'},
        },
        mode: 'GetDeleteCreate',
      },
    },
  },
}
