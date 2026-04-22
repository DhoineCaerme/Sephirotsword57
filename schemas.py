class LiveSystemState(BaseModel):
    active_ports: Optional[List[str]] = Field(
        default=[], 
        description="List of port numbers currently listening on the system."
    )
    installed_packages: Optional[List[str]] = Field(
        default=[], 
        description="List of required packages that are actually installed."
    )
    running_services: Optional[List[str]] = Field(
        default=[], 
        description="List of required services/containers that are actually running."
    )
    active_env_vars: Optional[List[EnvVar]] = Field(
        default=[], 
        description="List of required environment variables that are actually present."
    )