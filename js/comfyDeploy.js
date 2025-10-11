
class comfyDeploy extends LGraphNode {
    constructor() {
        super("Comfy Deploy");
        this.color = "#fbc02d"; // Yellow background for content
        this.bgcolor = "#f0da38"; // Darker yellow border
        this.groupcolor = "#f9a825"; // Group color

        this.properties = {
            workflow_name: "",
            workflow_id: "",
            version: ""
        };

        this.addWidget(
            "text",
            "workflow_name",
            this.properties.workflow_name,
            (v) => {
                this.properties.workflow_name = v;
            },
            { multiline: false }
        );

        this.addWidget(
            "text",
            "workflow_id",
            this.properties.workflow_id,
            (v) => {
                this.properties.workflow_id = v;
            },
            { multiline: false }
        );

        this.addWidget(
            "text",
            "version",
            this.properties.version,
            (v) => {
                this.properties.version = v;
            },
            { multiline: false }
        );

        this.widgets_start_y = 10;
        this.serialize_widgets = true;
        this.isVirtualNode = true;
    }

    onExecute() {
    }

    onSerialize(o) {
        if (!o.properties) {
            o.properties = {};
        }
        o.properties.workflow_name = this.properties.workflow_name;
        o.properties.workflow_id = this.properties.workflow_id;
        o.properties.version = this.properties.version;
    }

    onConfigure(o) {
        if (o.properties) {
            this.properties = { ...this.properties, ...o.properties };
            this.widgets[0].value = this.properties.workflow_name || "";
            this.widgets[1].value = this.properties.workflow_id || "";
            this.widgets[2].value = this.properties.version || "";
        }
    }

    onDrawBackground(ctx) {
        if (this.flags.collapsed) {
            return;
        }
    }
}

// Register the node type
LiteGraph.registerNodeType(
   "comfy-deploy/comfy-deploy",
   comfyDeploy,
    {
        title: "Comfy Deploy",
        title_mode: LiteGraph.NORMAL_TITLE,
        collapsable: true,
    }
);