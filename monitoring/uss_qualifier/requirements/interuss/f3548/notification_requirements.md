# ASTM F3548-21 notifications requirement

While ASTM F3548-21 does not specifically prohibit sending notifications for operational intent changes when those notifications were not specifically prescribed by a notification that an operational intent may be relevant to a subscription (response from the DSS), InterUSS expects that notifications will only be sent at these particular times.
SCD0085 requirement states only a positive requirement (preconditions satisified => notification must be sent).
It doesn't establish a negative requirement (preconditions not satisfied => no notifications may be sent).
As these negative requirements are reasonable  and related to SCD0085, interUSS has added it as a requirement for testing.
This can happen in following situations -
* <tt>NoDssEntityNoNotification</tt> If a USS was unable to write an entity reference to the DSS, it should not erroneously notify that operational intent, to another USS subscribed in the area.
* <tt>NoSubscriptionNoNotification</tt> If a USS wrote an entity reference to the DSS, and was notified of no other USS subscription, then it should not send a notification to any USS. So the USS  shall (OnlyPrescribedNotifications) only send operational intent notifications when prescribed by SCD0085.
