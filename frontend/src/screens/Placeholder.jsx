export default function Placeholder({ title }) {
  return (
    <section className="placeholder" aria-label={title}>
      <h1 className="h2">{title}</h1>
    </section>
  )
}
