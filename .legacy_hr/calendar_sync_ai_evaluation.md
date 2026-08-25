# Legacy Code: Calendar Sync AI Evaluation Trigger

This code block was previously commented out in `src/orchestrators/sync_calendar_to_graph.py` and has been moved here to clean up the orchestrator file while preserving the logic for future reference.

```python
            # --- AI EVALUATION TRIGGER (COMMENTED OUT FOR CORE FUNCTIONALITY) ---
            # Future Improvement: When the LLM evaluation logic is stabilized, uncomment this
            # section to re-enable daily batch classification via GTKYLibrarian and GTKYHistorian.
            #
            # # --- Stream A: Current & Future (Librarian) ---
            # recent_staged_cursor = timeseries_col.find({
            #     "start_time": {"$gte": start_of_day},
            #     "metadata.sync_status": "staged",
            #     "metadata.user_email": user_email
            # })
            # recent_staged_list = list(recent_staged_cursor)
            #
            # # --- Stream B: Historical Backlog (Historian) limit 100 per run ---
            # historic_staged_cursor = timeseries_col.find({
            #     "start_time": {"$lt": start_of_day},
            #     "metadata.sync_status": "staged",
            #     "metadata.user_email": user_email
            # }).sort("start_time", -1).limit(100)
            # historic_staged_list = list(historic_staged_cursor)
            #
            # def process_and_save_batch(staged_list, is_historical=False):
            #     if not staged_list:
            #         return
            #     raw_events = [e.get("raw_data", {}) for e in staged_list]
            #     user_doc = storage.get_user_by_email(user_email)
            #     username = user_doc.get("username", "unknown") if user_doc else "unknown"
            #
            #     if is_historical:
            #         logger.info(f"Historian found {len(raw_events)} historical events for {user_email}.")
            #         try:
            #             golden_objects = historian.classify_historical_batch(raw_events, username=username)
            #         except Exception as e:
            #             logger.info(f"Agent failed: {e}")
            #             golden_objects = []
            #     else:
            #         logger.info(f"Librarian found {len(raw_events)} recent events for {user_email}.")
            #         try:
            #             golden_objects = librarian.classify_daily_batch(raw_events, username=username)
            #         except Exception as e:
            #             logger.info(f"Agent failed: {e}")
            #             golden_objects = []
            #
            #     if not golden_objects:
            #         logger.info(f"Agents returned empty for {user_email}. Skipping this batch.")
            #         return
            #
            #     if golden_objects:
            #         formatted_ops = []
            #         daily_ops = []
            #         for obj in golden_objects:
            #             obj["user_email"] = user_email
            #             obj["username"] = username
            #             obj["gcal_pushed"] = False
            #             obj["gcal_push_timestamp"] = None
            #
            #             formatted_ops.append(UpdateOne({"gcal_id": obj.get('gcal_id')}, {"$set": obj}, upsert=True))
            #
            #             obj['status'] = "Pending Verification"
            #             daily_ops.append(UpdateOne({"gcal_id": obj.get('gcal_id')}, {"$set": obj}, upsert=True))
            #
            #         if formatted_ops: storage.formatted_col.bulk_write(formatted_ops, ordered=False)
            #         if daily_ops: daily_cat_col.bulk_write(daily_ops, ordered=False)
            #
            #     timeseries_ops = []
            #     for e in staged_list:
            #         gcal_id = e.get("metadata", {}).get("gcal_id")
            #         email = e.get("metadata", {}).get("user_email")
            #         if gcal_id and email:
            #             timeseries_ops.append(UpdateMany(
            #                 {"metadata.gcal_id": gcal_id, "metadata.user_email": email},
            #                 {"$set": {"metadata.sync_status": "formatted"}}
            #             ))
            #     if timeseries_ops: timeseries_col.bulk_write(timeseries_ops, ordered=False)
            #
            # process_and_save_batch(recent_staged_list, is_historical=False)
            # process_and_save_batch(historic_staged_list, is_historical=True)
            # --- END AI EVALUATION TRIGGER ---
```
