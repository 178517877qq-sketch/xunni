import { Command } from "@tauri-apps/plugin-shell";

export type WorkflowMode = "optimize-only" | "optimize-sync" | "sync-only" | "proxy-test";

export interface WorkflowCommand {
  program: string;
  args: string[];
  label: string;
}

const MAIN_SCRIPT = "main.py";

export function buildWorkflowCommand(mode: WorkflowMode, pythonPath = "python"): WorkflowCommand {
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
    return {
      program: pythonPath,
      args: [
        "-c",
        "import urllib.request,sys; proxy=sys.argv[1] if len(sys.argv)>1 else ''; opener=urllib.request.build_opener(urllib.request.ProxyHandler({'http':proxy,'https':proxy}) if proxy else urllib.request.ProxyHandler({})); opener.open('https://github.com', timeout=10); print('github.com ok')",
        ""
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

export async function runWorkflow(mode: WorkflowMode, pythonPath = "python") {
  const workflow = buildWorkflowCommand(mode, pythonPath);
  const command = Command.create(workflow.program, workflow.args, {
    cwd: "."
  });
  return command.execute();
}
