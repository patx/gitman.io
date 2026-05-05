% rebase("base.tpl", title="New repository", user=user, error=error, notice=notice)

<section class="auth-card wide">
  <h1>New repository</h1>
  <form method="post">
    {{!csrf_field()}}
    <label>
      Repository name
      <input name="name" value="{{name if defined('name') else ''}}" required pattern="[a-z0-9][a-z0-9._-]{1,62}">
    </label>
    <label>
      Description
      <textarea name="description" rows="3">{{description if defined("description") else ""}}</textarea>
    </label>
    <p class="muted">Repositories are public to clone and browse. You can add contributors after creation.</p>
    <button class="button" type="submit">Create repository</button>
  </form>
</section>
