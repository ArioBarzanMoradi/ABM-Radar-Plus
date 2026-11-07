import esbuild from "esbuild";
import {copyFile} from "node:fs/promises";
await esbuild.build({entryPoints:["frontend/entry.tsx"],bundle:true,minify:true,format:"esm",target:"es2022",outfile:"docs/assets/app.js",legalComments:"eof",define:{"process.env.NODE_ENV":'"production"'}});
await copyFile("frontend/style.css","docs/assets/style.css");
