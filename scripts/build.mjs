import esbuild from "esbuild";
import {readFile,writeFile} from "node:fs/promises";
await esbuild.build({entryPoints:["frontend/entry.tsx"],bundle:true,minify:true,format:"esm",target:"es2022",outfile:"docs/assets/app.js",legalComments:"eof",define:{"process.env.NODE_ENV":'"production"'}});
const css=await Promise.all(["frontend/palette.css","frontend/style.css","frontend/theme.css"].map(path=>readFile(path,"utf8")));
await writeFile("docs/assets/style.css",css.join("\n"));
