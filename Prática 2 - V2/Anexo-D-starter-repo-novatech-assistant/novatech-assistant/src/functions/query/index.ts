// Registro do trigger HTTP do query endpoint (Azure Functions v4).
// Separado de handler.ts para que importar a lógica em testes não dispare o
// registro no load. Este é o módulo que o host das Functions carrega.

import { app } from "@azure/functions";
import { queryHandler } from "./handler.js";

app.http("query", {
  methods: ["POST"],
  authLevel: "function",
  route: "query",
  handler: queryHandler,
});
