# ASTM F3411 DSS endpoint requirements

While neither ASTM F3411-19 nor F3411-22a explicitly require DSS implementations to implement all endpoints specified in Annex A4 (of each respective standard), InterUSS automated testing expects DSS implementations to implement all DSS endpoints specified in Annex A4.  Specifically:

* <tt>PutISA</tt>: The DSS implementation under test must implement the ability to create and update an Identification Service Area by ID in accordance with the API specified in Annex A4 of the respective standard.
* <tt>GetISA</tt>: The DSS implementation under test must implement the ability to retrieve an Identification Service Area by ID in accordance with the API specified in Annex A4 of the respective standard.
* <tt>DeleteISA</tt>: The DSS implementation under test must implement the ability to delete an Identification Service Area by ID in accordance with the API specified in Annex A4 of the respective standard.
* <tt>SearchISAs</tt>: The DSS implementation under test must implement the ability to search for Identification Service Areas meeting the specified criteria in accordance with the API specified in Annex A4 of the respective standard.
* <tt>PutSubscription</tt>: The DSS implementation under test must implement the ability to create a subscription in accordance with the API specified in Annex A4 of the respective standard.
* <tt>SearchSubscriptions</tt>: The DSS implementation under test must implement the ability to search for subscriptions in accordance with the API specified in Annex A4 of the respective standard.
