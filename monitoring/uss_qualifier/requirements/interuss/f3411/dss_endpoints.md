# ASTM F3411 DSS endpoint requirements

While neither ASTM F3411-19 nor F3411-22a explicitly require DSS implementations to implement all endpoints specified in Annex A4 (of each respective standard), InterUSS automated testing expects DSS implementations to implement all DSS endpoints specified in Annex A4.  Specifically:

* <tt>GetISA</tt>: The DSS implementation under test must implement the ability to retrieve an Identification Service Area by ID in accordance with the API specified in Annex A4 of the respective standard.
* <tt>SearchISAs</tt>: The DSS implementation under test must implement the ability to search for Identification Service Areas meeting the specified criteria in accordance with the API specified in Annex A4 of the respective standard.
* <tt>SubscriptionInitialNotificationIndex</tt>: The DSS implementation under test must set the `notification_index` at 0 for any newly created subscription.
* <tt>SubscriptionVersionFormat</tt>: The DSS implementation under test must use a string of 10 or more lower-cased alphanumeric characters for the `version` field of a subscription.
