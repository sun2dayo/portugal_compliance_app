frappe.pages["saft-pt-generator"].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		 title: __("SAF-T (PT) Generator"),
		 single_column: true
	});

	// Add filters
	page.add_field({
		fieldname: "fiscal_year",
		label: __("Fiscal Year"),
		fieldtype: "Link",
		options: "Fiscal Year",
		 reqd: 1,
		 change: function() {
			let fiscal_year = page.get_value("fiscal_year");
			 if (fiscal_year) {
				 frappe.db.get_doc("Fiscal Year", fiscal_year).then(doc => {
					 page.set_value("start_date", doc.year_start_date);
					 page.set_value("end_date", doc.year_end_date);
				 });
			 } else {
				 page.set_value("start_date", null);
				 page.set_value("end_date", null);
			 }
		 }
	});

	 page.add_field({
		 fieldname: "start_date",
		 label: __("Start Date"),
		 fieldtype: "Date",
		 description: __("Optional. Defaults to fiscal year start date.")
	 });

	 page.add_field({
		 fieldname: "end_date",
		 label: __("End Date"),
		 fieldtype: "Date",
		 description: __("Optional. Defaults to fiscal year end date.")
	 });

	 // Add Generate button
	 page.add_button(__("Generate SAF-T (PT) File"), function() {
		 let fiscal_year = page.get_value("fiscal_year");
		 let start_date = page.get_value("start_date");
		 let end_date = page.get_value("end_date");

		 if (!fiscal_year) {
			 frappe.msgprint({ title: __("Validation Error"), message: __("Please select a Fiscal Year."), indicator: "red" });
			 return;
		 }

		 // Optional: Validate start/end dates if provided
		 if (start_date && end_date && start_date > end_date) {
			 frappe.msgprint({ title: __("Validation Error"), message: __("Start Date cannot be after End Date."), indicator: "red" });
			 return;
		 }

		 frappe.show_alert({ message: __("Generating SAF-T file... This may take a few moments."), indicator: "blue" });

		 frappe.call({
			 method: "portugal_compliance.portugal_compliance.portugal_compliance.saft.generator.generate_saft_pt_file",
			 args: {
				 fiscal_year: fiscal_year,
				 start_date: start_date || null, // Send null if not provided
				 end_date: end_date || null
			 },
			 callback: function(r) {
				 if (r.message && r.message.filename && r.message.filecontent) {
					 frappe.msgprint({ title: __("Success"), message: __("SAF-T file generated successfully."), indicator: "green" });
					 frappe.download_file(r.message.filecontent, r.message.filename);
				 } else if (r._server_messages) {
					 // Error handled by frappe
				 } else {
					 frappe.msgprint({ title: __("Error"), message: __("Failed to generate SAF-T file. Check Error Log for details."), indicator: "red" });
				 }
			 },
			 error: function(r) {
				 frappe.msgprint({ title: __("Error"), message: __("An unexpected error occurred. Check Error Log for details."), indicator: "red" });
			 }
		 });
	 });

	 // Set default fiscal year (optional)
	 frappe.call({
		 method: "portugal_compliance.portugal_compliance.portugal_compliance.page.saft_pt_generator.get_fiscal_years",
		 callback: function(r) {
			 if (r.message && r.message.length > 0) {
				 // Set the most recent fiscal year as default
				 page.set_value("fiscal_year", r.message[0].name);
			 }
		 }
	 });

};

