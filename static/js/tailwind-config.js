window.tailwind = window.tailwind || {};
window.tailwind.config = {
    darkMode: "class",
    theme: {
        extend: {
            colors: {
                primary: "#003b5a",
                background: "#1e1e2f",
                surface: "#2d2d44",
                "on-surface": "#ffffff",
                "on-background": "#ffffff",
                "primary-container": "#1a5276",
                secondary: "#006497",
                error: "#ba1a1a",
                outline: "#72787f"
            },
            borderRadius: {
                DEFAULT: "0.25rem",
                lg: "12px",
                xl: "12px",
                full: "9999px"
            },
            spacing: {
                margin: "24px",
                xl: "32px",
                xs: "4px",
                md: "16px",
                sm: "12px",
                lg: "24px",
                base: "8px",
                gutter: "20px"
            },
            fontFamily: {
                "data-mono": ["monospace"],
                h2: ["Inter"],
                h3: ["Inter"],
                "body-main": ["Inter"],
                "label-bold": ["Inter"],
                "label-caps": ["Inter"],
                h1: ["Inter"],
                "body-compact": ["Inter"]
            },
            fontSize: {
                "data-mono": ["13px", { lineHeight: "1.4", fontWeight: "400" }],
                h2: ["24px", { lineHeight: "1.3", fontWeight: "600" }],
                h3: ["20px", { lineHeight: "1.4", fontWeight: "500" }],
                "body-main": ["16px", { lineHeight: "1.5", fontWeight: "400" }],
                "label-bold": ["12px", { lineHeight: "1.2", letterSpacing: "0.05em", fontWeight: "600" }],
                "label-caps": ["11px", { lineHeight: "1.2", fontWeight: "700" }],
                h1: ["32px", { lineHeight: "1.2", fontWeight: "600" }],
                "body-compact": ["14px", { lineHeight: "1.4", fontWeight: "400" }]
            }
        }
    }
};
