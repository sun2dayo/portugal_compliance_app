// document_series_pt.js

frappe.ui.form.on("Document Series PT", {
    refresh: function(frm) {
        // Add a custom button to the form if the document is saved and not already communicated successfully
        if (!frm.is_new() && frm.doc.communication_status !== "Communicated") {
            frm.add_custom_button(__("Comunicar Série à AT"), function() {
                frappe.call({
                    method: "portugal_compliance.utils.at_communication_service.communicate_serie_to_at",
                    args: {
                        doc_series_name: frm.doc.name
                    },
                    callback: function(r) {
                        if (r.message && r.message.status === "success") {
                            frappe.msgprint({
                                title: __("Sucesso"),
                                indicator: "green",
                                message: __("Série {0} comunicada com sucesso. Código de Validação: {1}").format([frm.doc.name, r.message.validation_code])
                            });
                            frm.reload_doc(); // Reload to see updated status and validation code
                        } else {
                            // Error already thrown by backend, Frappe handles it
                            // but we can show a generic message if needed, though usually not necessary
                            // frappe.msgprint({
                            //     title: __("Erro"),
                            //     indicator: "red",
                            //     message: __("Falha ao comunicar série: {0}").format([r.exc || "Erro desconhecido"])
                            // });
                        }
                    },
                    error: function(r) {
                        // Frappe usually handles this by showing the error message from the server
                        frappe.msgprint({
                            title: __("Erro de Comunicação"),
                            indicator: "red",
                            message: __("Ocorreu um erro ao tentar comunicar com o servidor.")
                        });
                    },
                    always: function() {
                        // You can re-enable the button or do other cleanup here if needed
                    }
                });
            }).addClass("btn-primary");
        }
    },
    // Example: Add validation before saving if needed
    // validate: function(frm) {
    //     if (frm.doc.some_condition) {
    //         frappe.msgprint("Validation error");
    //         frappe.validated = false;
    //     }
    // }
});

