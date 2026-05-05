% rebase("base.tpl", title="Fork " + source_repo["owner_username"] + "/" + source_repo["name"], user=user, error=error, notice=notice)

<section class="auth-card wide">
  <h1>Fork {{source_repo["owner_username"]}}/{{source_repo["name"]}}</h1>
  <form method="post">
    {{!csrf_field()}}
    <label>
      Repository name
      <input name="name" value="{{name}}" required pattern="[a-z0-9][a-z0-9._-]{1,62}">
    </label>
    <label>
      Description
      <textarea name="description" rows="3">{{description}}</textarea>
    </label>
    <button class="button" type="submit">Fork repository</button>
  </form>
</section>
