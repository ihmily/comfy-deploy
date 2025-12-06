
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
            if (this.widgets && this.widgets.length >= 3) {
                this.widgets[0].value = this.properties.workflow_name || "";
                this.widgets[1].value = this.properties.workflow_id || "";
                this.widgets[2].value = this.properties.version || "";
            }
        }
    }
    
    // Override setProperty for Vue nodes compatibility
    setProperty(name, value) {
        if (this.properties) {
            this.properties[name] = value;
        }
        
        // Update corresponding widget
        const widgetMap = {
            'workflow_name': 0,
            'workflow_id': 1,
            'version': 2
        };
        
        if (widgetMap.hasOwnProperty(name) && this.widgets) {
            const widgetIndex = widgetMap[name];
            if (this.widgets[widgetIndex]) {
                this.widgets[widgetIndex].value = value;
                if (this.widgets[widgetIndex].callback) {
                    this.widgets[widgetIndex].callback(value);
                }
            }
        }
        
        // Mark graph as dirty to trigger re-render
        if (this.graph) {
            this.graph.setDirtyCanvas(true, true);
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