import type { Metadata } from "next";
import { Roboto, Roboto_Mono } from "next/font/google";
import { ThemeProvider } from "next-themes";
import "./globals.css";
import "bpmn-js/dist/assets/diagram-js.css";
import "bpmn-js/dist/assets/bpmn-js.css";
import "bpmn-js/dist/assets/bpmn-font/css/bpmn.css";

const robotoSans = Roboto({
    variable: "--font-sans",
    subsets: ["latin"],
});

const robotoMono = Roboto_Mono({
    variable: "--font-mono",
    subsets: ["latin"],
});

export const metadata: Metadata = {
    title: "IMR Challenge",
    description:
        "IMR Challenge que cumple con la función de crear un chatbot para crear graficos BPMN",
    icons: "./icon.png",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
    return (
        <html
            lang="es"
            suppressHydrationWarning
            className={`${robotoSans.variable} ${robotoMono.variable} h-full antialiased`}
        >
            <body className="min-h-full flex flex-col">
                <ThemeProvider
                    attribute="class"
                    defaultTheme="system"
                    enableSystem
                    disableTransitionOnChange
                >
                    {children}
                </ThemeProvider>
            </body>
        </html>
    );
}
