// Limits a list of `participants` to only those whose `participant_id` appears in the provided `allow_list`
function(participants, allow_list) [
  p
  for p in participants
  if std.member(allow_list, p.participant_id)
]
