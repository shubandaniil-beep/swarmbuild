import ProjectForm from "@/components/ProjectForm";
import RequireAuth from "@/components/RequireAuth";

export default function NewProject() {
  return (
    <RequireAuth>
      <div className="max-w-3xl mx-auto">
        <p className="kicker mb-1">Запуск проекта</p>
        <h1 className="text-3xl font-bold tracking-tight">Новый проект</h1>
        <p className="mt-2 text-sm text-zinc-500 mb-8">
          Опишите результат простыми словами — система сама подготовит маршрут, проверки и итоговые файлы.
        </p>
        <ProjectForm />
      </div>
    </RequireAuth>
  );
}
