import { Command } from "@tauri-apps/plugin-shell";

export type WorkflowMode = "optimize-only" | "optimize-sync" | "sync-only" | "proxy-test";

export interface WorkflowCommand {
  program: string;
  args: string[];
  label: string;
}

export interface WorkflowOptions {
  pythonPath?: string;
  proxyUrl?: string;
}

const MAIN_SCRIPT = "main.py";

function resolvePythonPath(options: WorkflowOptions = {}, fallback = "python") {
  return options.pythonPath?.trim() || fallback;
}

export function buildWorkflowCommand(mode: WorkflowMode, options: WorkflowOptions = {}): WorkflowCommand {
  const pythonPath = resolvePythonPath(options);

  if (mode === "optimize-only") {
    return {
      program: pythonPath,
      args: ["-u", MAIN_SCRIPT, "--no-github-sync"],
      label: "只运行优选"
    };
  }

  if (mode === "sync-only") {
    return {
      program: pythonPath,
      args: ["-u", MAIN_SCRIPT, "--sync-only"],
      label: "上传到 GitHub"
    };
  }

  if (mode === "proxy-test") {
    const proxyUrl = options.proxyUrl?.trim() || "";
    return {
      program: pythonPath,
      args: [
        "-c",
        "import urllib.request,sys; proxy=sys.argv[1] if len(sys.argv)>1 else ''; opener=urllib.request.build_opener(urllib.request.ProxyHandler({'http':proxy,'https':proxy}) if proxy else urllib.request.ProxyHandler({})); opener.open('https://github.com', timeout=10); print('github.com ok')",
        proxyUrl
      ],
      label: "测试 GitHub 代理"
    };
  }

  return {
    program: pythonPath,
    args: ["-u", MAIN_SCRIPT],
    label: "优选后自动上传"
  };
}

export async function runWorkflow(mode: WorkflowMode, options: WorkflowOptions = {}) {
  const workflow = buildWorkflowCommand(mode, options);
  const command = Command.create(workflow.program, workflow.args, {
    cwd: "."
  });
  return command.execute();
}
